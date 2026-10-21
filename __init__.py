from . import models


def uninstall_hook(env):
    # réaffiche le menu Employés masqué par le module
    menu = env.ref('hr.menu_hr_root', raise_if_not_found=False)
    if menu:
        menu.active = True
