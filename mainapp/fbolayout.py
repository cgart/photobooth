

from kivy.uix.widget import Widget
from kivy.properties import ListProperty, ObjectProperty
from kivy.graphics.fbo import Fbo
from kivy.graphics.transformation import Matrix
from kivy.graphics.shader import *
from kivy.graphics.opengl import *
from kivy.graphics import *


class FboFloatLayout(Widget):

	texture = ObjectProperty(None, allownone=True)
	vertices = ListProperty([])
	
	fbo = None
	tmp_fbo = None 
	
	def __init__(self, **kwargs):
		
		self.canvas = Canvas()
		
		with self.canvas:
			self.fbo = Fbo(size=self.size)
			
		super(FboFloatLayout, self).__init__(**kwargs)

	# --
	# preload FBO with background texture
	def initFbo(self):
		
		with self.fbo:
			ClearColor(0,0,0,0)
			ClearBuffers()
			Rectangle(source = 'data/background.jpg', size=self.size, pos=self.pos)

		self.texture = self.fbo.texture
				
	# --
	# add the content of the widget to the FBO
	# this will literally render the widget into the texture
	def render_widget(self, widget):

		# create an FBO to render the widget to
		self.tmp_fbo = Fbo(size = self.size)
		self.tmp_fbo.add(ClearColor(0,0,0,0))
		self.tmp_fbo.add(ClearBuffers())
		self.tmp_fbo.add(widget.canvas)
		self.tmp_fbo.draw()

		# render a rectangle in the main fbo containing the content from the widget
		with self.fbo:
			Color(1,1,1,1)
			Rectangle(texture=self.tmp_fbo.texture, size=self.tmp_fbo.size)
					
	#def add_widget(self, *largs):
		# trick to attach graphics instruction to fbo instead of canvas
	#	canvas = self.canvas
	#	self.canvas = self.fbo
	#	ret = super(FboFloatLayout, self).add_widget(*largs)
	#	self.canvas = canvas
		
		# remove widget after next frame, this makes sure that 
		# we do not use the widget for more than one frame
		#Clock.schedule_once(lambda dt: self.remove_widget(*largs))

	#	return ret

	#def remove_widget(self, *largs):
	#	canvas = self.canvas
	#	self.canvas = self.fbo
	#	super(FboFloatLayout, self).remove_widget(*largs)
	#	self.canvas = canvas

	def on_size(self, instance, value):
		self.size = value 
		
		self.fbo.size = value
		
		#self.fbo_rect.size = value
		#self.fbo_background.size = value
		#self.fbo_rect.texture = self.fbo.texture
		
		# setup simple quad mesh to be rendered
		# the quad is used for actual resizing
		self.vertices = []
		self.vertices.extend([0,0,0,0])
		self.vertices.extend([0,self.height,0,1])
		self.vertices.extend([self.width,self.height,1,1])
		self.vertices.extend([self.width,0,1,0])

		#self.updateFbo()		
		self.initFbo()
		
	#def on_pos(self, instance, value):
		#self.fbo_rect.pos = value
		#self.fbo_background.pos = value
	#	pass
		
	#def on_texture(self, instance, value):
		#self.texture = value
	#	pass
		
	#def on_alpha(self, instance, value):
	#	self.fbo_color.rgba = (1, 1, 1, value)
