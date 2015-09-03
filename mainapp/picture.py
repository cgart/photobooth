from random import randrange, uniform, randint
import numpy as np

from kivy.graphics.shader import *
from kivy.graphics.opengl import *
from kivy.graphics import *
from kivy.graphics.fbo import Fbo
from kivy.uix.scatter import Scatter
from kivy.animation import Animation
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import ListProperty, ObjectProperty
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.loader import Loader

# todo - reconsider to remove it from here
from kivy.cache import Cache

# ----------------------------------------------------------------------
# Picture captured with camera
# ----------------------------------------------------------------------
class Picture(Scatter):
	
    img_texture = ObjectProperty()
    alpha = NumericProperty()
    onLoadCallback = None
    filename = None

    vertices = ListProperty([])

    fbo_texture = ObjectProperty(None)
    fbo = None

    border_image = None
    keep_aspect = True

    aspectRatio = 1.0

    # --
    def __init__(self, filename=None, onload=None, **kwargs):
        
        self.canvas = Canvas()
        
        with self.canvas:
            self.fbo = Fbo(size=(1024,1024))
            self.fbo.add_reload_observer(self.updateFbo)
            
        self.border_image = CoreImage('data/shadow32.png')
        self.img_texture = Texture.create(size=(16,16), colorfmt="rgba")		
                
        self.alpha = 0		
        self.fbo_texture = self.fbo.texture
        
        super(Picture, self).__init__(**kwargs)		
        
        self.loadImage(filename, onload)
        

    # --
    def updateFbo(self):
            
        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            Color(1,1,1,1)
            BorderImage(texture=self.border_image.texture, border=(36,36,36,36), size = (self.fbo.size[0], self.fbo.size[1]), pos=(0,0))
            Rectangle(texture=self.img_texture, size=(self.fbo.size[0]-72, self.fbo.size[1]-72), pos=(36,36))
                            
        self.fbo_texture = self.fbo.texture
        
        pass

    # --
    def on_size(self, instance, value):

        # change the underlying size property
        newAspectRatio = float(value[1]) / float(value[0])
        
        if self.keep_aspect:
            value[1] = value[0] * self.aspectRatio
            newAspectRatio = self.aspectRatio
                        
        self.size = value
        
        # setup simple quad mesh to be rendered
        # the quad is used for actual resizing
        self.vertices = []
        self.vertices.extend([0,0,0,0])
        self.vertices.extend([0,self.height,0,1])
        self.vertices.extend([self.width,self.height,1,1])
        self.vertices.extend([self.width,0,1,0])

        
        # if the aspect ratio of the underlying FBO is not the same as the aspect
        # ratio of the new size, then change the size of the FBO
        fboAspectRatio = float(self.fbo.size[1]) / float(self.fbo.size[0])
        
        if abs(fboAspectRatio - newAspectRatio) > 0.1:
            fboSize = (self.fbo.size[0], self.fbo.size[1] * newAspectRatio)
            self.fbo.size = fboSize
            self.updateFbo()
            
        pass

    # --
    def loadImage(self, filename, onload = None):
        self.filename = filename
        if filename != None:
            self.onLoadCallback = onload
                
            proxyImage = Loader.image(filename)
                    
            # this is totally stupid behaviour of Kivy
            # the docs suggest to bind proxy image's on_load method to a callback
            # to indicate when image is loaded. However, when image is already
            # in the cache the callback won't be called. My first thought was
            # that it was a threading issue, because the bindind might have happened
            # after the callback was initiated, but it seems that indeed the method is just not called.
            if proxyImage.loaded == False:
                proxyImage.bind(on_load=self._image_loaded)
            else:
                self._image_loaded(proxyImage)

    # --
    # All used memory except of the FBO texture is released. The image
    # can still be used, however, properties could not be changed
    def releaseMemory(self):
        
        self.img_texture = False
        self.border_image = False
        self.fbo_texture = Texture.create(size=(2,2), colorfmt="rgba")
                
        # clear up cache
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        Cache.remove('kv.loader')
            
        pass
        
    # --
    def _image_loaded(self, proxyImage):
        
        if proxyImage.image.texture:
            self.img_texture = proxyImage.image.texture
            self.aspectRatio = float(proxyImage.image.height) / float(proxyImage.image.width)
            self.updateFbo()
            
            anim = Animation(alpha=1, duration=0.2)
            anim.start(self)
            
            if self.onLoadCallback != None:
                self.onLoadCallback(self)

