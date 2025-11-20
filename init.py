### SAMURAI - Subprocess Edition (GPU Ready!)
import sys
import os
import nuke

# Plugin uses subprocess with system Python for GPU inference
# No torch imports in Nuke Python - keeps it clean and simple!

plugin_path = os.path.dirname(__file__)

# Add icons
nuke.pluginAddPath("./icons", addToSysPath=False)

print("[NukeSamurai] Plugin loaded (GPU via subprocess)")
###
