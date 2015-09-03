from kivy.uix.widget import Widget
from kivy.properties import NumericProperty

class WhiteBillboard(Widget):
		
	alpha = NumericProperty()
	
	def __init__(self, **kwargs):
		super(WhiteBillboard, self).__init__(**kwargs)
		self.alpha = 0
