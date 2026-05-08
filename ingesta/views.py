import logging
import threading
import traceback
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EvolutionInstance
from .services import IngestionService

logger = logging.getLogger(__name__)


SYNC_JOBS = {}
SYNC_JOBS_LOCK = threading.Lock()


def _update_job(job_id: str, **changes):
	with SYNC_JOBS_LOCK:
		job = SYNC_JOBS.get(job_id)
		if not job:
			return
		job.update(changes)


def _is_numeric(text: str) -> bool:
	"""Determina si un texto es puramente numérico (sin letras).
	
	Elimina espacios, + y - al principio, y verifica si solo contiene dígitos.
	Retorna True para vacío o None (se marca como número para usuarios sin nombre).
	"""
	if not text:
		return True
	cleaned = str(text).strip().lstrip("+-").replace(" ", "")
	return cleaned.isdigit() if cleaned else True


class SyncTriggerView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		instance_name = request.data.get("instance_name", "default")
		job_id = str(uuid.uuid4())
		with SYNC_JOBS_LOCK:
			SYNC_JOBS[job_id] = {
				"job_id": job_id,
				"instance_name": instance_name,
				"status": "queued",
				"progress": 0,
				"message": "Esperando inicio",
				"result": None,
				"error": None,
			}

		def runner():
			service = IngestionService(instance_name=instance_name)
			try:
				_update_job(job_id, status="running", progress=1, message="Iniciando tarea")

				def on_progress(percent, message):
					_update_job(job_id, status="running", progress=percent, message=message)

				result = service.sync_messages(progress_callback=on_progress)
				_update_job(
					job_id,
					status="completed",
					progress=100,
					message="Proceso completado",
					result=result,
				)
			except Exception as exc:
				logger.exception("Fallo en sincronizacion para job_id=%s", job_id)
				_update_job(
					job_id,
					status="failed",
					message="Error durante la sincronizacion",
					error=str(exc),
					traceback=traceback.format_exc(),
				)

		threading.Thread(target=runner, daemon=True).start()
		return Response(
			{
				"job_id": job_id,
				"status": "queued",
				"progress": 0,
				"message": "Tarea creada",
			},
			status=status.HTTP_202_ACCEPTED,
		)


class SyncStatusView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def get(self, request, job_id, *args, **kwargs):
		with SYNC_JOBS_LOCK:
			job = SYNC_JOBS.get(job_id)
		if not job:
			return Response(
				{"detail": "job_id no encontrado"},
				status=status.HTTP_404_NOT_FOUND,
			)
		return Response(job, status=status.HTTP_200_OK)


class InstancesListView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def get(self, request, *args, **kwargs):
		instances = EvolutionInstance.objects.filter(is_active=True).values("id", "instance_name", "description")
		return Response(
			list(instances),
			status=status.HTTP_200_OK,
		)


class SyncPageView(View):
	def get(self, request, *args, **kwargs):
		instances = EvolutionInstance.objects.filter(is_active=True).values("id", "instance_name", "description")
		first_instance = instances.first()
		default_instance_name = first_instance["instance_name"] if first_instance else None
		
		return render(
			request,
			"ingesta/sync.html",
			{
				"instances": list(instances),
				"default_instance_name": default_instance_name,
				"cors_allowed_origins": settings.CORS_ALLOWED_ORIGINS,
			},
		)


class CrmDashboardView(View):
	def get(self, request, *args, **kwargs):
		from .models import ChatUser, Message

		users_qs = ChatUser.objects.filter(is_customer=True)
		users_with_counts = list(
			users_qs.annotate(
				inbound_count=Count("messages", filter=Q(messages__from_me=False)),
				outbound_count=Count("messages", filter=Q(messages__from_me=True)),
				total_count=Count("messages"),
			)
		)

		named_users_count = users_qs.exclude(name__exact="").count()
		unnamed_users = list(users_qs.filter(name__exact="").order_by("-last_interaction")[:25])

		messages = list(
			Message.objects.select_related("user").filter(user__is_customer=True)
			.order_by("user_id", "timestamp")
			.values("user_id", "timestamp", "from_me")
		)

		response_samples = 0
		response_wait_total = timedelta(0)
		last_inbound_by_user = {}
		response_totals_by_user = {}
		response_samples_by_user = {}
		last_outbound_by_user = {}

		interaction_dates_by_user = {}
		for msg in messages:
			user_id = msg["user_id"]
			timestamp = msg["timestamp"]
			from_me = bool(msg["from_me"])

			interaction_dates_by_user.setdefault(user_id, set()).add(timestamp.date())

			if from_me:
				last_outbound_by_user[user_id] = timestamp
				pending = last_inbound_by_user.get(user_id)
				if pending and timestamp > pending:
					wait = timestamp - pending
					response_wait_total += wait
					response_samples += 1
					response_totals_by_user[user_id] = response_totals_by_user.get(user_id, timedelta(0)) + wait
					response_samples_by_user[user_id] = response_samples_by_user.get(user_id, 0) + 1
				last_inbound_by_user[user_id] = None
			else:
				last_inbound_by_user[user_id] = timestamp

		avg_response_days = 0.0
		if response_samples > 0:
			avg_response_days = response_wait_total.total_seconds() / 86400 / response_samples
		avg_response_hours = 0.0
		if response_samples > 0:
			avg_response_hours = response_wait_total.total_seconds() / 3600 / response_samples

		now = timezone.now()
		all_gaps = []
		for user in users_with_counts:
			dates = sorted(interaction_dates_by_user.get(user.id, set()))
			if len(dates) < 2:
				avg_gap = None
			else:
				gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
				avg_gap = sum(gaps) / len(gaps)
				all_gaps.extend(gaps)

			if user.last_interaction:
				days_since_last = (now.date() - user.last_interaction.date()).days
			else:
				days_since_last = None

			user.avg_gap_days = avg_gap
			user.interaction_days = len(dates)
			user.days_since_last_interaction = days_since_last
			user.last_our_action = last_outbound_by_user.get(user.id)
			if user.last_our_action:
				user.days_since_last_our_action = (now.date() - user.last_our_action.date()).days
			else:
				user.days_since_last_our_action = None

			user_response_samples = response_samples_by_user.get(user.id, 0)
			user_response_total = response_totals_by_user.get(user.id, timedelta(0))
			user.response_samples = user_response_samples
			if user_response_samples > 0:
				user.avg_our_response_hours = user_response_total.total_seconds() / 3600 / user_response_samples
				user.avg_our_response_days = user_response_total.total_seconds() / 86400 / user_response_samples
			else:
				user.avg_our_response_hours = None
				user.avg_our_response_days = None

		global_avg_gap_days = (sum(all_gaps) / len(all_gaps)) if all_gaps else 0.0

		avg_days_since_last = 0.0
		days_samples = [u.days_since_last_interaction for u in users_with_counts if u.days_since_last_interaction is not None]
		if days_samples:
			avg_days_since_last = sum(days_samples) / len(days_samples)

		most_stale_user = None
		max_days_since_last = 0
		if days_samples:
			most_stale_user = max(
				users_with_counts,
				key=lambda u: u.days_since_last_interaction if u.days_since_last_interaction is not None else -1,
			)
			max_days_since_last = most_stale_user.days_since_last_interaction or 0

		cold_users_30 = len([u for u in users_with_counts if (u.days_since_last_interaction or 0) >= 30])
		cold_users_90 = len([u for u in users_with_counts if (u.days_since_last_interaction or 0) >= 90])
		stale_10 = len([u for u in users_with_counts if (u.days_since_last_interaction or 0) >= 10])
		stale_20 = len([u for u in users_with_counts if (u.days_since_last_interaction or 0) >= 20])
		stale_40 = len([u for u in users_with_counts if (u.days_since_last_interaction or 0) >= 40])

		query = str(request.GET.get("q") or "").strip().lower()
		name_status = str(request.GET.get("name_status") or "all").strip().lower()
		sort_by = str(request.GET.get("sort_by") or "inbound").strip().lower()
		sort_dir = str(request.GET.get("sort_dir") or "desc").strip().lower()

		try:
			stale_min = int(request.GET.get("stale_min") or 0)
		except (TypeError, ValueError):
			stale_min = 0

		try:
			min_inbound = int(request.GET.get("min_inbound") or 0)
		except (TypeError, ValueError):
			min_inbound = 0

		try:
			min_outbound = int(request.GET.get("min_outbound") or 0)
		except (TypeError, ValueError):
			min_outbound = 0

		try:
			limit = int(request.GET.get("limit") or 50)
		except (TypeError, ValueError):
			limit = 50
		limit = max(10, min(250, limit))

		def matches_filters(user):
			user_name = str(user.name or "").strip()
			phone = str(user.phone_number or "").strip()
			wa_id = str(user.wa_id or "").strip()

			if query:
				blob = f"{user_name} {phone} {wa_id}".lower()
				if query not in blob:
					return False

			if name_status == "named" and not user_name:
				return False
			if name_status == "unnamed" and user_name:
				return False

			if (user.inbound_count or 0) < min_inbound:
				return False
			if (user.outbound_count or 0) < min_outbound:
				return False

			if stale_min > 0:
				if user.days_since_last_interaction is None or user.days_since_last_interaction < stale_min:
					return False

			return True

		filtered_users = [u for u in users_with_counts if matches_filters(u)]

		sort_map = {
			"name": lambda u: (str(u.name or "").lower(), u.id),
			"inbound": lambda u: ((u.inbound_count or 0), u.id),
			"outbound": lambda u: ((u.outbound_count or 0), u.id),
			"total": lambda u: ((u.total_count or 0), u.id),
			"avg_gap": lambda u: ((u.avg_gap_days if u.avg_gap_days is not None else -1), u.id),
			"avg_our_response": lambda u: ((u.avg_our_response_hours if u.avg_our_response_hours is not None else -1), u.id),
			"days_since_last": lambda u: ((u.days_since_last_interaction if u.days_since_last_interaction is not None else -1), u.id),
			"days_since_last_our_action": lambda u: ((u.days_since_last_our_action if u.days_since_last_our_action is not None else -1), u.id),
			"last_interaction": lambda u: ((u.last_interaction.timestamp() if u.last_interaction else -1), u.id),
			"last_our_action": lambda u: ((u.last_our_action.timestamp() if u.last_our_action else -1), u.id),
		}
		sort_key = sort_map.get(sort_by, sort_map["inbound"])
		reverse = sort_dir != "asc"
		filtered_users.sort(key=sort_key, reverse=reverse)

		top_users = filtered_users[:limit]
		
		# Agregar data_kind a cada usuario para el filtro de números/letras
		for user in top_users:
			user.data_kind = "numbers" if _is_numeric(user.name) else "letters"
		for user in unnamed_users:
			user.data_kind = "numbers" if _is_numeric(user.name) else "letters"
		
		stale_users = sorted(
			[u for u in users_with_counts if u.days_since_last_interaction is not None],
			key=lambda u: (u.days_since_last_interaction, u.id),
			reverse=True,
		)[:10]
		for user in stale_users:
			user.data_kind = "numbers" if _is_numeric(user.name) else "letters"

		labels = []
		inbound_data = []
		outbound_data = []
		for user in top_users[:10]:
			label = str(user.name or user.phone_number or user.wa_id)
			labels.append(label[:18] + "..." if len(label) > 18 else label)
			inbound_data.append(int(user.inbound_count or 0))
			outbound_data.append(int(user.outbound_count or 0))

		stale_bucket_counts = {
			"0-1 dias": 0,
			"2-7 dias": 0,
			"8-30 dias": 0,
			"31-90 dias": 0,
			"91-180 dias": 0,
			"181+ dias": 0,
		}
		for user in users_with_counts:
			days = user.days_since_last_interaction
			if days is None:
				continue
			if days <= 1:
				stale_bucket_counts["0-1 dias"] += 1
			elif days <= 7:
				stale_bucket_counts["2-7 dias"] += 1
			elif days <= 30:
				stale_bucket_counts["8-30 dias"] += 1
			elif days <= 90:
				stale_bucket_counts["31-90 dias"] += 1
			elif days <= 180:
				stale_bucket_counts["91-180 dias"] += 1
			else:
				stale_bucket_counts["181+ dias"] += 1

		stale_distribution = [
			{"label": label, "count": count}
			for label, count in stale_bucket_counts.items()
		]

		context = {
			"total_users": users_qs.count(),
			"total_messages": Message.objects.count(),
			"total_inbound": Message.objects.filter(from_me=False).count(),
			"total_outbound": Message.objects.filter(from_me=True).count(),
			"named_users_count": named_users_count,
			"unnamed_users_count": users_qs.count() - named_users_count,
			"top_users": top_users,
			"filtered_count": len(filtered_users),
			"filters": {
				"q": request.GET.get("q", ""),
				"name_status": name_status,
				"stale_min": stale_min,
				"min_inbound": min_inbound,
				"min_outbound": min_outbound,
				"sort_by": sort_by,
				"sort_dir": sort_dir,
				"limit": limit,
			},
			"global_avg_gap_days": global_avg_gap_days,
			"avg_response_days": avg_response_days,
			"avg_response_hours": avg_response_hours,
			"avg_days_since_last": avg_days_since_last,
			"max_days_since_last": max_days_since_last,
			"most_stale_user": most_stale_user,
			"cold_users_30": cold_users_30,
			"cold_users_90": cold_users_90,
			"stale_10": stale_10,
			"stale_20": stale_20,
			"stale_40": stale_40,
			"response_samples": response_samples,
			"stale_users": stale_users,
			"chart_labels": labels,
			"chart_inbound": inbound_data,
			"chart_outbound": outbound_data,
			"stale_distribution": stale_distribution,
			"unnamed_users": unnamed_users,
		}

		return render(request, "ingesta/crm_dashboard.html", context)


class CrmUserDetailView(View):
	def get(self, request, user_id, *args, **kwargs):
		from .models import ChatUser, DailyTextSummary, Message, MonthlyTextSummary

		user = get_object_or_404(ChatUser, id=user_id, is_customer=True)
		all_messages_qs = Message.objects.filter(user=user)
		media_types = [Message.MessageType.AUDIO, Message.MessageType.IMAGE, Message.MessageType.VIDEO]
		no_media_filter = Q(message_type__in=media_types) & (Q(media_file="") | Q(media_file__isnull=True))
		encrypted_media_filter = Q(message_type__in=media_types) & Q(media_file__iendswith=".enc")
		visible_messages_qs = all_messages_qs.exclude(no_media_filter | encrypted_media_filter)

		recent_messages = list(visible_messages_qs.order_by("-timestamp")[:40])
		inbound_messages = list(visible_messages_qs.filter(from_me=False).order_by("-timestamp")[:20])
		outbound_messages = list(visible_messages_qs.filter(from_me=True).order_by("-timestamp")[:20])

		total_messages = all_messages_qs.count()
		inbound_count = all_messages_qs.filter(from_me=False).count()
		outbound_count = all_messages_qs.filter(from_me=True).count()
		no_media_count = all_messages_qs.filter(no_media_filter).count()
		encrypted_media_count = all_messages_qs.filter(encrypted_media_filter).count()
		available_media_count = all_messages_qs.filter(message_type__in=media_types).exclude(media_file="").exclude(media_file__isnull=True).exclude(media_file__iendswith=".enc").count()

		first_message = all_messages_qs.order_by("timestamp").first()
		latest_message = all_messages_qs.order_by("-timestamp").first()

		now = timezone.now()
		days_since_last = None
		if user.last_interaction:
			days_since_last = (now.date() - user.last_interaction.date()).days

		ordered_values = list(
			all_messages_qs.order_by("timestamp").values("timestamp", "from_me", "content", "message_type")
		)

		response_samples = 0
		response_wait_total = timedelta(0)
		last_inbound = None
		interaction_dates = []
		last_our_action = None

		for msg in ordered_values:
			ts = msg["timestamp"]
			interaction_dates.append(ts.date())

			if msg["from_me"]:
				last_our_action = ts
				if last_inbound and ts > last_inbound:
					response_wait_total += ts - last_inbound
					response_samples += 1
				last_inbound = None
			else:
				last_inbound = ts

		avg_response_days = 0.0
		if response_samples > 0:
			avg_response_days = response_wait_total.total_seconds() / 86400 / response_samples
		avg_response_hours = 0.0
		if response_samples > 0:
			avg_response_hours = response_wait_total.total_seconds() / 3600 / response_samples

		days_since_last_our_action = None
		if last_our_action:
			days_since_last_our_action = (now.date() - last_our_action.date()).days

		unique_dates = sorted(set(interaction_dates))
		avg_gap_days = None
		if len(unique_dates) >= 2:
			gaps = [(unique_dates[i] - unique_dates[i - 1]).days for i in range(1, len(unique_dates))]
			if gaps:
				avg_gap_days = sum(gaps) / len(gaps)

		message_type_rows = list(
			all_messages_qs.values("message_type")
			.annotate(total=Count("id"))
			.order_by("-total", "message_type")
		)

		daily_summaries = list(
			DailyTextSummary.objects.filter(user=user)
			.order_by("-summary_date")[:14]
		)
		monthly_current_summary = (
			MonthlyTextSummary.objects.filter(user=user, is_current=True)
			.order_by("-year", "-month", "-revision")
			.first()
		)

		context = {
			"user": user,
			"total_messages": total_messages,
			"inbound_count": inbound_count,
			"outbound_count": outbound_count,
			"no_media_count": no_media_count,
			"encrypted_media_count": encrypted_media_count,
			"available_media_count": available_media_count,
			"first_message": first_message,
			"latest_message": latest_message,
			"days_since_last": days_since_last,
			"avg_response_days": avg_response_days,
			"avg_response_hours": avg_response_hours,
			"avg_gap_days": avg_gap_days,
			"last_our_action": last_our_action,
			"days_since_last_our_action": days_since_last_our_action,
			"interaction_days": len(unique_dates),
			"response_samples": response_samples,
			"message_type_rows": message_type_rows,
			"recent_messages": recent_messages,
			"inbound_messages": inbound_messages,
			"outbound_messages": outbound_messages,
			"daily_summaries": daily_summaries,
			"monthly_current_summary": monthly_current_summary,
			"name_updated": request.GET.get("updated") == "1",
		}
		return render(request, "ingesta/crm_user_detail.html", context)

	def post(self, request, user_id, *args, **kwargs):
		from .models import ChatUser

		user = get_object_or_404(ChatUser, id=user_id, is_customer=True)
		new_name = str(request.POST.get("name") or "").strip()
		user.name = new_name
		user.save(update_fields=["name"])
		return redirect(f"/ingesta/crm/user/{user.id}/?updated=1")


class ChatUserRenameView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		from .models import ChatUser

		user_id = request.data.get("user_id")
		name = str(request.data.get("name") or "").strip()

		if not user_id:
			return Response({"detail": "user_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)

		try:
			user = ChatUser.objects.get(id=user_id, is_customer=True)
		except ChatUser.DoesNotExist:
			return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

		user.name = name
		user.save(update_fields=["name"])
		return Response(
			{
				"id": user.id,
				"wa_id": user.wa_id,
				"phone_number": user.phone_number,
				"name": user.name,
				"display_label": user.display_label(),
			},
			status=status.HTTP_200_OK,
		)


class SummaryTriggerView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		from datetime import timedelta

		from .summary_service import TextSummaryService
	
		lookback_hours = int(request.data.get("lookback_hours", 12))
		force = bool(request.data.get("force", False))
		accumulate = bool(request.data.get("accumulate", True))
		job_id = str(uuid.uuid4())
	
		with SYNC_JOBS_LOCK:
			SYNC_JOBS[job_id] = {
				"job_id": job_id,
				"type": "summary",
				"status": "queued",
				"progress": 0,
				"message": "Esperando inicio",
				"result": None,
				"error": None,
			}
	
		def runner():
			try:
				_update_job(job_id, status="running", progress=10, message="Iniciando resúmenes IA")
				
				now = timezone.now()
				slot_end = now
				
				service = TextSummaryService()
				if accumulate:
					slot_start, window_meta = service.compute_accumulation_window(
						slot_end=slot_end,
						fallback_lookback_hours=lookback_hours,
					)
				else:
					slot_start = slot_end - timedelta(hours=lookback_hours)
					window_meta = {
						"mode": "fixed_lookback",
						"today_start": None,
						"oldest_pending_day": None,
						"has_today_text": None,
					}

				run_key = f"manual_{job_id}"

				mode_label = {
					"accumulation_pending_backlog": "acumulacion historica + hoy",
					"today_refresh": "actualizacion de hoy",
					"fallback_lookback": "ventana fallback",
					"fixed_lookback": "ventana fija",
				}.get(window_meta.get("mode"), "procesamiento")

				_update_job(
					job_id,
					status="running",
					progress=15,
					message=f"Preparando {mode_label}",
				)

				def on_summary_progress(state):
					total = max(1, int(state.get("eligible_users") or 0))
					done = int(state.get("processed_users") or 0) + int(state.get("failed_users") or 0) + int(state.get("skipped_users") or 0)
					if state.get("phase") == "processing_days":
						current_user_index = int(state.get("current_user_index") or 1)
						day_total = max(1, int(state.get("current_user_total_days") or 1))
						day_done = max(0, min(day_total, int(state.get("current_user_day_done") or 0)))
						effective_done = min(total, (current_user_index - 1) + (day_done / day_total))
					else:
						effective_done = done

					pct = 15 + int((effective_done / total) * 80)
					pct = max(15, min(95, pct))
					_update_job(
						job_id,
						status="running",
						progress=pct,
						message=(
							f"Resumiendo usuarios ({done}/{total}) - {mode_label}"
						),
					)

				log = service.run_for_slot(
					slot_start=slot_start,
					slot_end=slot_end,
					run_key=run_key,
					force=force,
					progress_callback=on_summary_progress,
				)
				log.meta = {
					**(log.meta or {}),
					**window_meta,
				}
				log.save(update_fields=["meta"])
				
				daily_rows = list(log.daily_summaries.select_related("user").order_by("user_id", "summary_date"))
				monthly_rows = list(log.monthly_summaries.select_related("user").order_by("user_id", "year", "month", "-revision"))

				daily_report = []
				for row in daily_rows:
					label = row.user.name or row.user.phone_number or row.user.wa_id
					daily_report.append(
						{
							"user_id": row.user_id,
							"chat": label,
							"date": row.summary_date.isoformat(),
							"has_data": row.has_data,
							"source_message_count": row.source_message_count,
							"tokens": row.total_tokens,
							"text": row.text,
						}
					)

				monthly_report = []
				for row in monthly_rows:
					label = row.user.name or row.user.phone_number or row.user.wa_id
					monthly_report.append(
						{
							"user_id": row.user_id,
							"chat": label,
							"year": row.year,
							"month": row.month,
							"revision": row.revision,
							"has_data": row.has_data,
							"source_message_count": row.source_message_count,
							"tokens": row.total_tokens,
							"text": row.text,
						}
					)

				result = {
					"run_key": log.run_key,
					"status": log.status,
					"eligible_users": log.eligible_users,
					"processed_users": log.processed_users,
					"failed_users": log.failed_users,
					"daily_summaries_created": log.daily_summaries_created,
					"daily_summaries_updated": log.daily_summaries_updated,
					"monthly_summaries_created": log.monthly_summaries_created,
					"monthly_summaries_updated": log.monthly_summaries_updated,
					"total_tokens": log.total_tokens,
					"slot_start": slot_start.isoformat(),
					"slot_end": slot_end.isoformat(),
					"window_mode": window_meta.get("mode"),
					"window_oldest_pending_day": window_meta.get("oldest_pending_day"),
					"window_has_today_text": window_meta.get("has_today_text"),
					"window_step_hours": window_meta.get("accumulation_step_hours"),
					"window_cursor_start": window_meta.get("accumulation_cursor_start"),
					"window_reached_oldest": window_meta.get("accumulation_reached_oldest"),
					"daily_generated": daily_report,
					"monthly_generated": monthly_report,
				}
				
				_update_job(
					job_id,
					status="completed",
					progress=100,
					message=f"Resúmenes IA completados ({window_meta.get('mode')})",
					result=result,
				)
			except Exception as exc:
				logger.exception("Fallo en resúmenes IA para job_id=%s", job_id)
				_update_job(
					job_id,
					status="failed",
					message="Error durante resúmenes IA",
					error=str(exc),
					traceback=traceback.format_exc(),
				)
	
		threading.Thread(target=runner, daemon=True).start()
		return Response(
			{
				"job_id": job_id,
				"status": "queued",
				"progress": 0,
				"message": "Tarea de resúmenes creada",
			},
			status=status.HTTP_202_ACCEPTED,
		)


class AudioBriefingTriggerView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		from .audio_service import AudioBriefingService
		from .models import ChatUser

		instance_name = str(request.data.get("instance_name") or "default").strip()
		raw_team_user_id = request.data.get("team_user_id")
		try:
			team_user_id = int(raw_team_user_id) if raw_team_user_id not in (None, "", "null") else None
		except (TypeError, ValueError):
			team_user_id = None
		job_id = str(uuid.uuid4())

		with SYNC_JOBS_LOCK:
			SYNC_JOBS[job_id] = {
				"job_id": job_id,
				"type": "audio_briefing",
				"instance_name": instance_name,
				"status": "queued",
				"progress": 0,
				"message": "Esperando inicio",
				"result": None,
				"error": None,
			}

		def runner():
			try:
				_update_job(job_id, status="running", progress=10, message="Inicializando audio briefing")

				team_user = None
				if team_user_id:
					team_user = ChatUser.objects.filter(id=team_user_id).first()
					if not team_user:
						_update_job(
							job_id,
							status="running",
							progress=12,
							message=f"team_user_id={team_user_id} no existe, usando fallback automático",
						)

				if not team_user:
					team_user = ChatUser.objects.filter(is_customer=False).order_by("-last_interaction", "id").first()

				if not team_user:
					team_user = ChatUser.objects.order_by("-last_interaction", "id").first()

				if not team_user:
					raise ValueError("No hay usuario de equipo disponible para generar el briefing")

				service = AudioBriefingService()

				def on_audio_progress(state: dict):
					pct = max(10, min(95, int(state.get("progress") or 10)))
					phase = str(state.get("phase") or "proceso")
					detail = str(state.get("detail") or "")
					_update_job(
						job_id,
						status="running",
						progress=pct,
						message=f"Audio briefing [{phase}] {detail}".strip(),
					)

				result = service.generate_daily_briefing(
					instance_name=instance_name,
					team_user=team_user,
					date=timezone.now(),
					force_local_only=True,
					progress_callback=on_audio_progress,
				)

				if result.get("error"):
					raise RuntimeError(result["error"])

				audio_file = str(result.get("audio_file") or "").lstrip("/")
				media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
				if not media_url.endswith("/"):
					media_url = f"{media_url}/"
				if audio_file:
					result["audio_download_url"] = f"{media_url}{audio_file}"
				result["selected_team_user"] = {
					"id": team_user.id,
					"display_label": team_user.display_label(),
				}
				result["delivery_mode"] = "download_only"

				_update_job(
					job_id,
					status="completed",
					progress=100,
					message="Audio briefing completado (descarga local)",
					result=result,
				)
			except Exception as exc:
				logger.exception("Fallo en audio briefing para job_id=%s", job_id)
				_update_job(
					job_id,
					status="failed",
					message="Error durante audio briefing",
					error=str(exc),
					traceback=traceback.format_exc(),
				)

		threading.Thread(target=runner, daemon=True).start()
		return Response(
			{
				"job_id": job_id,
				"status": "queued",
				"progress": 0,
				"message": "Tarea de audio briefing creada",
			},
			status=status.HTTP_202_ACCEPTED,
		)


class HomeView(View):
	def get(self, request, *args, **kwargs):
		endpoints = [
			{
				"method": "GET",
				"path": "/",
				"description": "Home funcional con guia del sistema y enlaces utiles.",
			},
			{
				"method": "GET",
				"path": "/ingesta/sync/",
				"description": "UI para ejecutar sincronizacion manual y ver progreso en vivo.",
			},
			{
				"method": "GET",
				"path": "/ingesta/crm/",
				"description": "Dashboard CRM con metricas de mensajes, tiempos y calidad de nombres.",
			},
			{
				"method": "GET",
				"path": "/ingesta/crm/user/<user_id>/",
				"description": "Detalle completo por contacto: info, metricas y mensajes recientes.",
			},
			{
				"method": "POST",
				"path": "/ingesta/api/sync/",
				"description": "Dispara una sincronizacion asincrona y devuelve job_id.",
			},
			{
				"method": "GET",
				"path": "/ingesta/api/sync/<job_id>/status/",
				"description": "Consulta estado, porcentaje y resultado final del job.",
			},
			{
				"method": "GET",
				"path": "/api/docs/",
				"description": "Catalogo de endpoints REST en formato JSON.",
			},
		]

		return render(
			request,
			"home.html",
			{
				"app_title": "SAMA AdTech - Ingesta WhatsApp",
				"endpoints": endpoints,
			},
		)


class EndpointDocsView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def get(self, request, *args, **kwargs):
		return Response(
			{
				"name": "SAMA Ingestion API",
				"version": "sprint-1",
				"endpoints": [
					{
						"method": "POST",
						"path": "/ingesta/api/sync/",
						"body": {"instance_name": "default"},
						"response": {
							"job_id": "uuid",
							"status": "queued",
							"progress": 0,
							"message": "Tarea creada",
						},
					},
					{
						"method": "GET",
						"path": "/ingesta/crm/",
						"description": "Dashboard CRM operativo para seguimiento comercial.",
					},
					{
						"method": "GET",
						"path": "/ingesta/crm/user/<user_id>/",
						"description": "Ficha de contacto con historial y edicion de nombre.",
					},
					{
						"method": "GET",
						"path": "/ingesta/api/sync/<job_id>/status/",
						"response": {
							"job_id": "uuid",
							"instance_name": "default",
							"status": "queued|running|completed|failed",
							"progress": 0,
							"message": "texto",
							"result": {},
							"error": "texto|null",
						},
					},
					{
						"method": "POST",
						"path": "/ingesta/api/chat-users/rename/",
						"body": {"user_id": 1, "name": "Nombre cliente"},
						"response": {
							"id": 1,
							"wa_id": "521...@s.whatsapp.net",
							"phone_number": "521...",
							"name": "Nombre cliente",
							"display_label": "Nombre cliente (521...)",
						},
					},
				],
				"notes": [
					"La sincronizacion es incremental y paginada desde Evolution API.",
					"El cursor se controla con IngestionControl.last_sync_timestamp por instancia.",
					"Deduplicacion por Message.external_id (unico).",
				],
			},
			status=status.HTTP_200_OK,
		)
