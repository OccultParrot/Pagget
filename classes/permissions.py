import inspect
from discord.app_commands import Command

def has_admin_check(command: Command) -> bool:
    """Check if a command has the admin check."""
    if not hasattr(command, 'checks') or not command.checks:
        return False

    for check in command.checks:
        # Check if the check is a has_permissions check with administrator=True
        if inspect.isfunction(check) and hasattr(check, '__closure__'):
            for cell in check.__closure__ or []:
                if cell.cell_contents == {'administrator': True}:
                    return True
    return False