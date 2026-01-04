
class VortexColors:
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

VORTEX_BANNER = r"""
        ____   ____              __                __________  __________   
        \   \ /   /___________ _/  |_  _______  __ \______   \ \______   \  
         \   Y   /  _ \_  __ \\   __\/ __ \  \/  /  |    |  _/  |    |  _/  
          \     (  <_> )  | \/ |  | \  ___/ >    <   |    |   \  |    |   \  
           \___/ \____/|__|    |__|  \___  >__/\_ \  |______  /  |______  /  
                                         \/      \/         \/          \/   
"""

def get_vortex_banner():
    """Returns a styled VortexDB ASCII banner."""
    styled_banner = f"{VortexColors.CYAN}{VortexColors.BOLD}{VORTEX_BANNER}{VortexColors.ENDC}"
    styled_banner += f"{VortexColors.BLUE}{VortexColors.BOLD}       >>> Unified Vector Database Solution for AI Applications <<<{VortexColors.ENDC}\n"
    return styled_banner

def print_vortex_banner():
    """Prints the VortexDB banner to the console."""
    print(get_vortex_banner())
