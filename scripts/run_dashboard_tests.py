#!/usr/bin/env python
"""
Script para ejecutar tests de drag & drop del dashboard.
Verifica dependencias, ejecuta tests y genera reporte.
"""

import os
import sys
import subprocess
from pathlib import Path

# Colores para output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_dependency(module_name, pip_name=None):
    """Verifica si un módulo está instalado."""
    try:
        __import__(module_name)
        print(f"{GREEN}✓{RESET} {module_name}")
        return True
    except ImportError:
        pip_package = pip_name or module_name
        print(f"{RED}✗{RESET} {module_name} (instalar: pip install {pip_package})")
        return False

def check_django_setup():
    """Verifica que Django está configurado."""
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
            django.setup()
        print(f"{GREEN}✓{RESET} Django configured")
        return True
    except Exception as e:
        print(f"{RED}✗{RESET} Django config: {e}")
        return False

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Dashboard Drag & Drop Tests - Pre-flight Check{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Verificar dependencias
    print(f"{YELLOW}Checking dependencies...{RESET}")
    deps_ok = all([
        check_dependency('pytest'),
        check_dependency('selenium'),
        check_dependency('webdriver_manager'),
        check_dependency('django'),
    ])
    
    print(f"\n{YELLOW}Checking Django setup...{RESET}")
    django_ok = check_django_setup()
    
    if not deps_ok:
        print(f"\n{RED}Some dependencies are missing!{RESET}")
        print(f"{YELLOW}Run: pip install pytest selenium webdriver-manager{RESET}")
        sys.exit(1)
    
    if not django_ok:
        print(f"\n{RED}Django not properly configured!{RESET}")
        sys.exit(1)
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Ready to run tests!{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Opciones de ejecución
    print(f"{YELLOW}Test Options:{RESET}")
    print(f"  1. Run all tests (may take 10-15 min)")
    print(f"  2. Run drag & drop tests only (5 min)")
    print(f"  3. Run filter tests only (5 min)")
    print(f"  4. Run single test (test number)")
    print(f"  5. Exit")
    
    choice = input(f"\n{BLUE}Select option (1-5):{RESET} ").strip()
    
    base_cmd = ["pytest", "crm/tests/test_drag_drop_real.py"]
    
    if choice == "1":
        cmd = base_cmd + ["-v", "--tb=short"]
    elif choice == "2":
        cmd = base_cmd + ["::TestDragDropRealBehavior", "-v", "--tb=short"]
    elif choice == "3":
        cmd = base_cmd + ["::TestFiltersFunctional", "-v", "--tb=short"]
    elif choice == "4":
        test_num = input(f"{BLUE}Enter test number (1-17):{RESET} ").strip()
        # Mapping de números a tests
        tests = {
            "1": "test_drag_card_from_lead_to_calificacion_no_refresh_needed",
            "2": "test_drag_backward_calificacion_to_lead",
            "3": "test_drag_multiple_times_forward_backward",
            "7": "test_filter_time_period_hoy_shows_only_today",
            "8": "test_filter_time_period_7d_hides_old_leads",
            "10": "test_filter_stage_unchecked_hides_cards",
        }
        if test_num in tests:
            cmd = base_cmd + [f"::{tests[test_num]}", "-v", "--tb=short"]
        else:
            print(f"{RED}Invalid test number{RESET}")
            sys.exit(1)
    else:
        print(f"{YELLOW}Exiting...{RESET}")
        sys.exit(0)
    
    print(f"\n{BLUE}Executing: {' '.join(cmd)}{RESET}\n")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
