from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import ListProperty, ObjectProperty
from kivy.core.text import Label as CoreLabel
from kivy.animation import Animation

# ----------------------------------------------------------------------
# Widget animating a number in the center of the screen
# ----------------------------------------------------------------------
class CounterNum(Widget):
	
	label = ObjectProperty(None)
	texture_size = None
	label_texture = ObjectProperty(None)
	
	def __init__(self, num, **kwargs):
		super(CounterNum, self).__init__(**kwargs)
		
		# generate texture containing the desired label
		self.label = CoreLabel(text=str(num), font_size=500, color=(1,1,1,1))
		self.label.refresh()		
		self.texture_size = list(self.label.texture.size)
		self.label_texture = self.label.texture
		
		pass
		
	def animate(self):
		
		# animate widget
		size_old = self.texture_size
		size_new = (size_old[0] * 1.5, size_old[1] * 1.5)
		pos = self.pos
		anim = Animation(size=size_new, pos=(pos[0] - (size_new[0] - size_old[0])/2, pos[1] - (size_new[1] - size_old[1])/2), duration=0.5)
		#anim = Animation(scale=1.5, pos=(pos[0] - (size_new[0] - size_old[0])/2, pos[1] - (size_new[1] - size_old[1])/2), duration=0.25)
		anim.start(self)

		pass
