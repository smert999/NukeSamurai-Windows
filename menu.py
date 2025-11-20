import nuke

### SAMURAI
from scripts.nuke_samurai import CreateSamuraiNode, UpdatePath, GenerateMask, BoundingBox, InputInfos

m = nuke.menu('Nodes')
m = m.addCommand('SAMURAI', 'CreateSamuraiNode()', tooltip="SAMURAI", icon="samurai_icon.png")
###