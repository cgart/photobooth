import piggyphoto

from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import ListProperty, ObjectProperty
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image

        
# ----------------------------------------------------------------------
# Preview widget - showing the current preview picture
# ----------------------------------------------------------------------
class Preview(Widget):
	
    camera = None
    preview_image = ObjectProperty()
    image = Image()
    alpha = NumericProperty()
    preview_file = 'preview.jpg'
    enable_preview = False
    
    def __init__(self, **kwargs):
        super(Preview, self).__init__(**kwargs)
        self.alpha = 0
        
    # ------------------------------------------------------------------
    def setCamera(self, capturePreviewFile = 'preview.jpg', camera = None):
        
        self.preview_file = capturePreviewFile
        self.image = Image(source = capturePreviewFile)
        self.camera = camera
        self.alpha = 0
        
        if camera != None:
            self.camera.capture_preview(capturePreviewFile)
            
        pass
        
    # ------------------------------------------------------------------
    def enablePreview(self):
        self.enable_preview = True
        
    # ------------------------------------------------------------------
    def disablePreview(self):
        self.enable_preview = False
        
    # ------------------------------------------------------------------
    def show(self):
        self.alpha = 1.
        
    # ------------------------------------------------------------------
    def hide(self):
        self.alpha = 0.
        
    # ------------------------------------------------------------------
    def updateFrame(self):

        if self.alpha < 0.1 or self.enable_preview == False:
            return
            
        if self.camera != None:
            self.camera.capture_preview(self.preview_file)

        self.image.reload()
        self.preview_image.texture = self.image.texture

        pass
