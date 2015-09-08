

# Kivy libraries
from kivy.uix.effectwidget import EffectWidget, EffectBase

from helpers import WhiteBillboard

glow_effect = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{
    vec4 f = vec4(0., 0., 0., 1.);
    vec2 u = coords;
	u /= resolution.xy;
    f.xy = vec2(u.x + 0.5, u.y);

    float t = time * 0.5,
          z = atan(f.y,f.x) * (sin(time * 0.5) + .3),
          v = cos(z + sin(t * .1)) + 2.5 + sin(u.x * 10.) * .4;

    f.x = cos(z - t*1.2) * 0.5 + sin(u.y*0.1+t*0.5)*.5;
	f.y = sin(v*2.)*.15 + f.x*0.5;
    f.z = sin(v*2.)*.3 + f.x*0.5;

    f.xyz *= 0.3;
    
    return vec4(f.x,f.y,f.z,1);
}
'''


class FullScreenEffect(EffectWidget):

    last_effect_list = None
    
    def __init__(self, *args, **kwargs):
        super(FullScreenEffect, self).__init__(*args, **kwargs)
        self.add_widget(WhiteBillboard(size=self.size))
    
    def show(self):
        if len(self.effects) == 0:
            self.effects = self.last_effect_list
            self.last_effect_list = []
        pass
        
    def hide(self):
        if len(self.effects) > 0:
            self.last_effect_list = self.effects
            self.effects = []
            
        pass
 
        
class ColorGlowEffect(EffectBase):
	
    def __init__(self, *args, **kwargs):
        super(ColorGlowEffect, self).__init__(*args, **kwargs)
        self.glsl = glow_effect
        
