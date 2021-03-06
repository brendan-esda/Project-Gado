from Tkinter import *
import tkFileDialog
import ttk
import tkFont
from gado.functions import *
import time
from threading import Thread
import gado.messages as messages
import Image, ImageTk
import Pmw

#Constants
WINDOW_HEIGHT = 300
WINDOW_WIDTH = 450

TEXT_HEIGHT = 10
TEXT_WIDTH = 50

class WizardQueueListener(Thread):
    def __init__(self, q_in, q_out, message, args, callback):
        self.q_in = q_in
        self.q_out = q_out
        self.message = message
        self.args = args
        self.callback = callback
        Thread.__init__(self)
    
    def run(self):
        if self.message == messages.WEBCAM_LISTING: track = True
        else: track = True
        
        if track:
            print 'WizardQueueListener\ttrack=True, message=%s' % self.message
        add_to_queue(self.q_out, self.message, self.args)
        if track:
            print 'WizardQueueListener\tadded message to the queue'
        msg = fetch_from_queue(self.q_in)
        if track:
            print 'WizardQueueListener\tfetched message from queue', msg
        self.callback(msg)
        
class ImageSampleViewer(Frame):
    def __init__(self, root, path):
        self.path = path
        self.root = root
        Frame.__init__(self, self.root)
                
        print 'ImageSampleViewer\tOpening image'
        image = Image.open(path)
        print 'ImageSampleViewer\tResizing image'
        image.thumbnail((500, 500), Image.ANTIALIAS)
        
        print 'ImageSampleViewer\tPhotoImage(image)'
        image_tk = ImageTk.PhotoImage(image)
        print 'ImageSampleViewer\tCreating the image\'s label'
        image_label = Label(self, image=image_tk)
        print 'ImageSampleViewer\tAssiging image_tk to .photo'
        image_label.photo = image_tk
        print 'ImageSampleViewer\tAdding the label to the grid'
        image_label.grid(row=0, column = 0, sticky=N+S+E+W, padx=10, pady=5)
        
        print 'ImageSampleViewer\tSetting up window closing protocol'
        window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        print 'ImageSampleViewer\tWithdrawing the window'
        window.withdraw()
        print 'ImageSampleViewer\t__init__ completed'
    
    def show():
        self.window.deiconify()
    

IN_PILE = 'Documents to be Scanned Pile'
OUT_PILE = 'Scanned Documents Pile'
SCANNER = 'Scanner'
SCANNER_HEIGHT = 'Scanner Height'

class Wizard():
    def __init__(self, root, q_in, q_out, q_gui):
        self.q_in = q_in # read by wizard
        self.q_out = q_out # goes to gado_sys
        self.q_gui = q_gui # goes to GadoGui
        self.root = root
        
        self._last_time = time.time()
        
        #Define our custom fonts
        labelFont = tkFont.Font(family = "Helvetica", size = 14)
        textFont = tkFont.Font(family="Helvetica", size = 11)
        self.labelFont = labelFont
        self.textFont = textFont
        
        #Set base size requirements
        window = Toplevel(root)
        window.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        #window.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        window.geometry("%dx%d+0+0" % (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.window = window
        
        #List to hold all frames
        frameList = []
        self.frameList = frameList
        self.frame_idx = 0
        nextButtons = []
        self.nextButtons = nextButtons
        
        self.keyboardCallbacks = dict()
        
        frame, next_btn = self._frame_image_path()
        frameList.append(frame)
        nextButtons.append(next_btn)
        #'''
        frame, next_btn = self._frame_welcome()
        frameList.append(frame)
        nextButtons.append(next_btn)
        #'''
        frame, next_btn = self._frame_requirements()
        frameList.append(frame)
        nextButtons.append(next_btn)
        #'''
        frame, next_btn = self._frame_peripheral('webcam')
        frameList.append(frame)
        nextButtons.append(next_btn)
        #'''
        frame, next_btn = self._frame_peripheral('scanner')
        frameList.append(frame)
        nextButtons.append(next_btn)
        #'''
        frame, next_btn = self._frame_location(IN_PILE)
        frameList.append(frame)
        nextButtons.append(next_btn)
        self.keyboardCallbacks[len(frameList) - 1] = 'arm_in_value'
        
        frame, next_btn = self._frame_location(SCANNER)
        frameList.append(frame)
        nextButtons.append(next_btn)
        self.keyboardCallbacks[len(frameList) - 1] = 'arm_home_value'
        
        frame, next_btn = self._frame_location(SCANNER_HEIGHT)
        frameList.append(frame)
        nextButtons.append(next_btn)
        self.keyboardCallbacks[len(frameList) - 1] = 'actuator_home_value'
        
        frame, next_btn = self._frame_location(OUT_PILE)
        frameList.append(frame)
        nextButtons.append(next_btn)
        self.keyboardCallbacks[len(frameList) - 1] = 'arm_out_value'
        
        frame, next_btn = self._frame_done()
        frameList.append(frame)
        nextButtons.append(next_btn)
        
        self.currentFrame = frame
        self.frame_idx = -1
        #self.nextFrame()
        
        window.protocol("WM_DELETE_WINDOW", self._quit)
        window.withdraw()
        
    def _set_webcam(self, a):
        idx = self.webcam_dropdown.curselection()[0]
        name = self.webcams[int(idx)][1]
        export_settings(webcam_name=name)
        print 'Wizard\tI just saved the webcam_name as %s' % name
    
    def webcam_options(self, msg):
        opts = msg[1]
        self.webcams = opts
        self.webcam_dropdown.delete(0, 'end')
        for opt in opts:
            self.webcam_dropdown.insert('end', opt[1])
        pass
    
    def load(self):
        for frame in self.frameList:
            frame.grid_forget()
        self.frameList[0].grid(column = 0, row = 0, padx = 10, pady = 5, sticky = N+S+E+W)
        self.currentFrame = self.frameList[0]
        self.frame_idx = 0
        self.window.deiconify()
        
        t = WizardQueueListener(self.q_in, self.q_out, messages.WEBCAM_LISTING, None, self.webcam_options)
        t.start()
        #self.root.mainloop()
    
    ##############################################################################
    ###                             WIDGET FUNCTIONS                           ###
    ##############################################################################
    
    def emptyFrame(self, label_text, main_text, text_height = TEXT_HEIGHT):
        frame = ttk.Frame(self.window, width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
        frame.grid(column=0, row=0, padx=10, pady=5, sticky=N+S+E+W)
        
        label = Label(frame, text=label_text, font=self.labelFont)
        label.grid(column=0, row=0, padx=10, pady=5, sticky=N+S+E+W, columnspan=2)
        
        text = Text(frame, height=text_height, width=TEXT_WIDTH, wrap=WORD, font=self.textFont)
        text.insert(END, main_text)
        text.config(state=DISABLED)
        text.grid(column=0, row=1, columnspan=2, padx=10, pady=20,sticky=N+S+E+W)
        
        return frame
    
    def nextButton(self, frame):
        button = Button(frame, text = "Next", command = self.nextFrame)
        return button
    
    def prevButton(self, frame):
        button = Button(frame, text = "Previous", command = self.prevFrame)
        return button
    
    def _frame_welcome(self):
        label = 'Welcome to the Gado Configuration Wizard!'
        text = '\n\nWe\'re going to try and connect the robot to your computer.\n\nPlease make sure it is plugged in...'
        frame = self.emptyFrame(label, text)
        
        #Nav buttons
        connect = Button(frame, text = "Connect", command = self.connectToGado)
        connect.grid(column = 0, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        next_btn = self.nextButton(frame)
        next_btn.config(state=DISABLED)
        next_btn.grid(column = 1, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, next_btn)
    
    def _frame_requirements(self):
        label = 'Setup Requirements'
        text = "In order to proceed with the setup you will need to make sure that you have:\n\
                       \n\t1. The piece of paper containing the QR code (tells the robot to stop)\
                       \n\t2. A sample of the typical kind of artifact you will be scanning\
                       \n\t3. All pieces of equipment that came with the robot\
                       \n\t4. A Smile :)"
        frame = self.emptyFrame(label, text)
        
        #Nav Buttons
        reqNextButton = self.nextButton(frame)
        reqBackButton = self.prevButton(frame)
        
        reqNextButton.grid(column = 1, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        reqBackButton.grid(column = 0, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, reqNextButton)
    
    def _frame_peripheral(self, p_type):
        # Two peripherals, webcam and scanner
        text = "\n\nWe're going to try to figure out which %s to use\
                \n\nMake sure that your %s is connected to your computer and that all necessary drivers are installed" % (p_type.lower(), p_type.lower())
        label = 'Connect to %s' % p_type.capitalize()
        frame = self.emptyFrame(label, text, text_height=TEXT_HEIGHT - 2)
        
        if 'scanner' in p_type.lower():
            funct = self.connectToScanner
            funct_2 = self.displayScannerSample
        elif 'webcam' in p_type.lower():
            funct = self.connectToWebcam
            funct_2 = self.displayWebcamSample
        
            webcams = Pmw.ComboBox(frame, selectioncommand=self._set_webcam)
            webcams.grid(row=1, column=0, sticky=N+S+E+W, padx=10, pady=5, columnspan=1)
            self.webcam_dropdown = webcams
            
        
        connect = Button(frame, text = "Locate %s" % (p_type.capitalize()),
                         command = funct)
        connect.grid(column = 1, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        sample = Button(frame, text = "Take Sample Picture",
                         command = funct_2)
        sample.grid(column = 2, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        nextButton = self.nextButton(frame)
        prevButton = self.prevButton(frame)
        
        nextButton.config(state=DISABLED)
        
        nextButton.grid(column = 1, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        prevButton.grid(column = 0, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, nextButton)
    
    def _frame_location(self, location):
        label = 'Configure the Robot'
        if location == SCANNER_HEIGHT:
            text = '\n\nUsing the up and down arrow keys, please place the suction cup on the scanner. We recommend placing a piece of paper on top of the scanner as you lower the suction cup.'
        else:
            text = '\n\nUsing the right and left arrow keys, please move the robot\'s arm over the %s' % location
        frame = self.emptyFrame(label, text)
        
        self.window.bind("<Key>", self._keyboard_callback)
        
        nextButton = self.nextButton(frame)
        prevButton = self.prevButton(frame)
        nextButton.grid(column = 1, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        prevButton.grid(column = 0, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, nextButton)
    
    def _frame_done(self):
        label = 'Finished!'
        text = "\n\nCongratulations! You have successfully configured the Gado!\n\nIn the future, if you would like to change the configuration, run this wizard again."
        frame = self.emptyFrame(label, text)
        
        doneQuitButton = Button(frame, text = "Done", command = self.nextFrame)
        doneBackButton = self.prevButton(frame)
        
        doneQuitButton.grid(column = 1, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        doneBackButton.grid(column = 0, row = 2, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, doneQuitButton)
    
    def _frame_image_path(self):
        frame = ttk.Frame(self.window, width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
        frame.grid(column=0, row=0, padx=10, pady=5, sticky=N+S+E+W)
        
        label = Label(frame, text='Where should images be saved?', font=self.labelFont)
        label.grid(column=0, row=0, padx=10, pady=5, sticky=N+S+E+W, columnspan=2)
        
        name_textbox = Entry(frame)
        name_textbox.grid(row=1, column=0, sticky=N+S+E+W, padx=10, pady=5)
        self.name_textbox = name_textbox
        name_textbox.config(state=DISABLED)
        
        button = Button(frame, text = "Browse", command = self.loadtemplate, width = 10)
        button.grid(column = 1, row = 1, padx = 10, pady = 5, sticky = N+S+E+W)
        
        nextButton = self.nextButton(frame)
        prevButton = self.prevButton(frame)
        
        nextButton.grid(column = 1, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        prevButton.grid(column = 0, row = 3, padx = 10, pady = 5, sticky = N+S+E+W)
        
        return (frame, nextButton)
    
    def loadtemplate(self):
        dirname = tkFileDialog.askdirectory(parent=self.root,
                                            initialdir=".",
                                            title='Please select a directory')
        print 'Wizard\tGot a directory name!'
        self.name_textbox.config(state=NORMAL)
        self.name_textbox.delete(0, 'end')
        self.name_textbox.insert('end', dirname)
        self.name_textbox.config(state=DISABLED)
        export_settings(image_path=dirname)
    
    def nextFrame(self):
        print 'Wizard\tnextFrame() called'
        print 'Wizard\tnextFrame() forgetting current frame'
        self.currentFrame.grid_forget()
        self.frame_idx += 1
        print 'Wizard\tnextFrame() next index: %s' % self.frame_idx
        if self.frame_idx >= len(self.frameList):
            print 'Wizard\tnextFrame() END OF THE ROAD'
            # We're done with all the frames
            self._quit()
            return
        print 'Wizard\tnextFrame() is this a keyboard callback?'
        nextFrame = self.frameList[self.frame_idx]
        print 'Wizard\tnextFrame() forcing nextFrame to be visible'
        nextFrame.grid(column = 0, row = 0, padx = 10, pady = 5, sticky = N+S+E+W)
        self.currentFrame = nextFrame
    
    def prevFrame(self):
        self.currentFrame.grid_forget()
        self.frame_idx -= 1
        if self.frame_idx < 0: self.frame_idx = 0
        nextFrame = self.frameList[self.frame_idx]
        nextFrame.grid(column = 0, row = 0, padx = 10, pady = 5, sticky = N+S+E+W)
        self.currentFrame = nextFrame
    
    def _quit(self):
        add_to_queue(self.q_gui, messages.RELAUNCH_LISTENER)
        self.window.destroy()
        
    ##############################################################################
    ###                             LOCATION SETUP FUNCTIONS                   ###
    ##############################################################################
    
    def _configuring_arm(self):
        return 'arm' in self.keyboardCallbacks[self.frame_idx]
    
    def _keyboard_callback(self, event):
        print 'Wizard\tKeyboard Event!'
        t = time.time()
        value = None
        settings_key = self.keyboardCallbacks[self.frame_idx]
        if t - self._last_time > 0.1:
            key = event.keycode
            self._last_time = t
            if self._configuring_arm():
                if key == 37:
                    #Left arrow press
                    #add_to_queue(self.q_out, messages.MOVE_LEFT)
                    value = self.robot.move_arm(clockwise=False)
                    print "Wizard\tarm move left to %s" % value
                    
                elif key == 39:
                    #add_to_queue(self.q_out, messages.MOVE_RIGHT)
                    value = self.robot.move_arm(clockwise=True)
                    #Right arrow press
                    print "Wizard\tarm move right to %s" % value
            else:
                if key == 38:
                    #add_to_queue(self.q_out, messages.MOVE_UP)
                    #Up arrow press
                    value = self.robot.move_actuator(up=True)
                    print "Wizard\tactuator move up to %s" % value
                elif key == 40:
                    #add_to_queue(self.q_out, messages.MOVE_DOWN)
                    #Down arrow press
                    value = self.robot.move_actuator(up=False)
                    print "Wizard\tactuator move down to %s" % value
            if value != None:
                print 'Wizard\tValue != None'
                s = {settings_key : value}
                print 'Wizard\tsettings:', s
                export_settings(**s)
    
    ##############################################################################
    ###                             WRAPPER FUNCTIONS                          ###
    ##############################################################################
    
    def connectToGado(self):
        #We can move on from the connection frame (Hardcoded to true until we have real connectivity)
        t = WizardQueueListener(self.q_in, self.q_out, messages.ROBOT_CONNECT, None, self.robotConnectCallback)
        t.start()
    
    def robotConnectCallback(self, msg):
        if msg[0] == messages.RETURN:
            if msg[1]:
                self.nextButtons[self.frame_idx].config(state=NORMAL)
                t = WizardQueueListener(self.q_in, self.q_out, messages.GIVE_ME_A_ROBOT, None, self.robotCallback)
                t.start()
    
    def robotCallback(self, msg):
        print 'Wizard\tgot a robot callback'
        if msg[0] == messages.RETURN:
            if msg[1]:
                print 'Wizard\tassigned self.robot'
                self.robot = msg[1]
    
    def connectToScanner(self):
        t = WizardQueueListener(self.q_in, self.q_out, messages.SCANNER_CONNECT, None, self.connectedCallback)
        t.start()
    
    def displayScannerSample(self):
        t = WizardQueueListener(self.q_in, self.q_out, messages.SCANNER_PICTURE, None, self.displayCallbackScanner)
        t.start()
    
    def displayWebcamSample(self):
        t = WizardQueueListener(self.q_in, self.q_out, messages.WEBCAM_PICTURE, None, self.displayCallbackWebcam)
        t.start()
    
    def displayCallbackWebcam(self, msg):
        #print 'Wizard\tCalling ImageSampleViewer with self.window and msg[1] "%s"' % msg[1]
        #ImageSampleViewer(self.window, msg[1])
        #print 'Wizard\tFinished calling ImageSampleViewer'
        add_to_queue(self.q_gui, messages.SET_WEBCAM_PICTURE, msg[1])
        #print 'Wizard\tCalling ImageSampleViewer with self.root and msg[1] "%s"' % msg[1]
        #viewer = ImageSampleViewer(self.window, msg[1])
        #print 'Wizard\tFinished calling ImageSampleViewer, calling show()'
        #viewer.show()
        #print 'Wizard\tFinished calling show()'
    
    def displayCallbackScanner(self, msg):
        add_to_queue(self.q_gui, messages.SET_SCANNER_PICTURE, msg[1])
    
    def connectToWebcam(self):
        t = WizardQueueListener(self.q_in, self.q_out, messages.WEBCAM_CONNECT, None, self.connectedCallback)
        t.start()
    
    def connectedCallback(self, msg):
        if msg[0] == messages.RETURN:
            if msg[1]:
                self.nextButtons[self.frame_idx].config(state=NORMAL)
                return
        add_to_queue(self.q_gui, messages.DISPLAY_ERROR, 'Unable to connect, please make sure everything is plugged in')
