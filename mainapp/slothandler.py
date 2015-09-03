from random import randrange, uniform, randint
from threading import Thread, Lock
import numpy as np
import glob

from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import ListProperty, ObjectProperty
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock

from .picture import Picture

# ----------------------------------------------------------------------
# All slots of captured images are handled by this class
# ----------------------------------------------------------------------
class CapturedSlots(Widget):

    alpha = NumericProperty()
    pictureList = []
    currentIdx = 0
    layout = ObjectProperty(None)
    cells = None
    num_x = 16
    num_y = 9
    cell_w = 0
    cell_h = 0
    mutex = Lock()
    root = None 

    image_path = ''

    # constructor
    def __init__(self, **kwargs):
        
        super(CapturedSlots, self).__init__(**kwargs)
        self.alpha = 1.0

    def setImageFilePath(self, filePath):
        self.image_path = filePath
        
    # prefill all slots with already taken images in chronological order
    def preloadSlots(self):
        
        # setup cell matrix with possible possible picture spots
        self.cells = [[None] * self.num_x for i in range(self.num_y)]
        self.cell_w = self.width / self.num_x
        self.cell_h = self.height / self.num_y
        
        # find all files
        files = glob.glob(self.image_path + '/*.jpg')
        files = sorted(files)

        print('screen: %dx%d' % (self.width, self.height))
        print('cells: %dx%d' % (self.cell_w, self.cell_h))
        
        # for each child of type picture load image
        for child in self.layout.children:
            if type(child) is Picture:
                self.pictureList.append(child)
                
        # update all slots
        if len(files) > 0:			
            for filename in files:
                self.populateNextSlot(filename)
                pass
                
    # update image in the next slot - if all slots are full, then start from beginning		
    def populateNextSlot(self, filename):

        # add new picture spread randomly over the screen
        newpic = Picture()
        newpic.center_x = self.width/2
        newpic.center_y = self.height/2
        newpic.filename = filename 
        
        self.addExistingImage(newpic)

    # add a new image into a random slot.
    # the image will be animated from its current position and scale down
    # to the required by the slot
    def addExistingImage(self, picture, onImageRenderedInto = None):

        self.mutex.acquire()
        
        # find a random cell where we put the image into
        cell = (randint(0, self.num_x-1), randint(0, self.num_y-1))
        poscntr = ((cell[0] + 0.5) * self.cell_w, (cell[1] + 0.5) * self.cell_h)
        rot = uniform(-35,35)
        
        
        # remove any images in the cell
        if self.cells[cell[1]][cell[0]] != None:
            wdgt = self.cells[cell[1]][cell[0]]
            #self.layout.remove_widget(wdgt)
        
        # add image as widget into the main root first, because
        # we want to keep it animated for a while
        self.cells[cell[1]][cell[0]] = picture
        self.root.add_widget(picture)
        
        self.mutex.release()
        
        # start animation of the image to be positioned in the slot
        # when animation stops we burn the image into the FloatLayout
        def _animate(pic):
            anim = Animation(center_x=poscntr[0], center_y=poscntr[1], width = 800, rotation = randint(0,2) * 360 + rot, duration=1.7)
            anim.start(pic)

            # ensure that the widget 
            # make sure that we render the picture into the main layout only once 
            # and then remove the used texture - this ensures smaller memory footprint
            def _addImageToLayout(anim, pic, on_cmpl):
                self.root.remove_widget(pic)
                self.layout.render_widget(pic)
                
                Clock.schedule_once(lambda dt: pic.releaseMemory(), 1.)
                
                if on_cmpl != None:
                    on_cmpl(anim, pic)
                
            anim.bind(on_complete = lambda a,w: _addImageToLayout(a,w,onImageRenderedInto))
            
            
        picture.loadImage(picture.filename, lambda pic: _animate(pic))
                            
        pass
        
    pass
