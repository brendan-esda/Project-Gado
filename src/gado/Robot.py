import serial, platform, time, sys, json

#Constants
MOVE_ARM = 'a'
MOVE_ACTUATOR = 's'
MOVE_VACUUM = 'v'
RETURN_CURRENT_SETTINGS = 'd'
DROP_ACTUATOR = 'p'

HANDSHAKE = 'h' # checks to see if we're actually talking to the robot
LOWER_AND_LIFT = 'l' # runs a routine on the robot to pick up an artifact
PLACE_ON_SCANNER = '2' # runs a routine to move an artifact to the scanner
DROP_ON_OUT_PILE = '3' # runs a routine to drop on the out pile
RESET_TO_HOME = '4' # runs a routine to move the arm home

HANDSHAKE_VALUE = 'Im a robot!'


ACTUATOR_LOWER_BOUNDS = 0
ACTUATOR_UPPER_BOUNDS = 255

ARM_LOWER_BOUNDS = 0
ARM_UPPER_BOUNDS = 190 # can we increase this?

class Robot(object):
    def __init__(self, arm_home_value=0, arm_in_value=0, arm_out_value=0, actuator_home_value=30, baudrate=115200, actuator_up_value=20, gado_port=None, **kargs):
        #Grab settings
        self.arm_home_value = arm_home_value
        self.arm_in_value = arm_in_value
        self.arm_out_value = arm_out_value
        self.actuator_home_value = actuator_home_value
        self.baudrate = baudrate
        self.actuator_up_value = actuator_up_value
        self.serialConnection = None
        self.current_arm_value = arm_home_value
        self.current_actuator_value = actuator_up_value
        
        if gado_port is not None:
            self.gado_port = gado_port
            self.connect(gado_port)
        
    #Take in a dictionary of all of the robot settings and make these the current settings
    #It is important that all robot specific settings are passed, otherwise things may break
    def updateSettings(self, **kwargs):
        
        #try and update
        try:
            self.arm_home_value = kwargs['arm_home_value']
            self.arm_in_value = kwargs['arm_in_value']
            self.arm_out_value = kwargs['arm_out_value']
            self.actuator_home_value = kwargs['actuator_home_value']
            self.actuator_up_value = kwargs['actuator_up_value']
            self.baudrate = kwargs['baudrate']
        except:
            print "Robot\tError when trying to update robot settings... (Make sure all settings were passed)\n Error: %s" % sys.exc_info()[0]
        
    def returnGadoInfo(self):
        if self.serialConnection.isOpen():
            self.clearSerialBuffers()
            self.serialConnection.write(RETURN_CURRENT_SETTINGS)
            time.sleep(0.1)
            response = self.serialConnection.read(1000)
            return response
        else:
            return ""
        
    def connect(self, port):
        '''
        Connects to the physcial robot on a certain COM port
        Returns true if it hears back correctly, else false
        '''
        
        if self.connected():
            return True
        
        try:
            #Open a serial connection to this serial port
            self.serialConnection = serial.Serial(port, self.baudrate, timeout=1)
        except:
            #raise
            print "Robot\tERROR CONNECTING TO SERIAL PORT: %s. Error: %s" % (port, sys.exc_info()[0])
            return False
        
        #Delay for 2 seconds because pyserial can't immediately communicate
        time.sleep(2)
        
        if self.serialConnection.isOpen():
            print "Robot\tInside robot connect"
            #Initiate the handshake with the (potential) robot
            self.serialConnection.flush()
            self.serialConnection.flushInput()
            self.serialConnection.flushOutput()
            self.serialConnection.write(HANDSHAKE)
            
            #give it a second to respond
            time.sleep(1)
            
            #Read back response (if any) and check to see if it matches the expected value
            response = self.serialConnection.read(100)
            
            print "Robot\tresponse: \"%s\"" % response
            
            if response.find(HANDSHAKE_VALUE) >= 0:
                self._moveArm(self.arm_home_value)
                return True
        return False
    
    def disconnect(self):
        if self.serialConnection.isOpen():
            self.serialConnection.close()
    
    def connected(self):
        '''
        Checks to see if the robot is connected
        '''
        if self.serialConnection and self.serialConnection.isOpen():
            #self.serialConnection.
            self.serialConnection.write(HANDSHAKE)
            
            #Read back response from (tentative) robot
            response = self.serialConnection.read(200)
            print "Robot\tGot serial response: %s, with port %s and baud %s" % (response, self.serialConnection.port, self.serialConnection.baudrate)
            
            if response.find(HANDSHAKE_VALUE) >= 0:
                return True
            
        #self.serialConnection = False
        return False
    
    def move_actuator(self, up):
        if up: # retracting the actuator moves it up
            n = self.current_actuator_value - 1
        else: # extending moves it down
            n = self.current_actuator_value + 1
        return self._moveActuator(n)
    
    def move_arm(self, clockwise):
        if clockwise:
            n = self.current_arm_value + 1
        else:
            n = self.current_arm_value - 1
        return self._moveArm(n)
    
    def drop_actuator(self):
        self._vacuumOn(True)
        self.serialConnection.write('%s' % DROP_ACTUATOR)
        self.clearSerialBuffers()
    
    def _drop(self):
        self.serialConnection.write('%s' % DROP_ON_OUT_PILE)
        self.clearSerialBuffers()
    
    #Move the robot's arm to the specified degree (between 0-180)
    def _moveArm(self, degree):
        if degree < ACTUATOR_LOWER_BOUNDS:
            degree = ACTUATOR_LOWER_BOUNDS
        elif degree > ACTUATOR_UPPER_BOUNDS:
            degree = ACTUATOR_UPPER_BOUNDS
        self.serialConnection.write("%s%s" % (degree, MOVE_ARM))
        self.current_arm_value = degree
        #Flush the serial line so we don't get any overflows in the event
        #that many commands are trying to be sent at once
        self.clearSerialBuffers()
        return degree
        
    
    #Move the robot's actuator to the specified stroke
    def _moveActuator(self, stroke):
        if stroke < ACTUATOR_LOWER_BOUNDS:
            stroke = ACTUATOR_LOWER_BOUNDS
        elif stroke > ACTUATOR_UPPER_BOUNDS:
            stroke = ACTUATOR_UPPER_BOUNDS
        self.serialConnection.write("%s%s" % (stroke, MOVE_ACTUATOR))
        self.current_actuator_value = stroke
        #Flush the serial line so we don't get any overflows in the event
        #that many commands are trying to be sent at once
        self.clearSerialBuffers()
        return stroke
        
        
    #Turn on the vacuum to the power level: value
    def _vacuumOn(self, value):
        self.serialConnection.write("%s%s" % (255 if value else 0, MOVE_VACUUM))
    
    #Clear all buffers on the serial line
    def clearSerialBuffers(self):        
        if self.serialConnection.isOpen():
            self.serialConnection.flushInput()
            self.serialConnection.flushOutput()
            self.serialConnection.flush()
    
    #Reset the robot to the home position
    def reset(self):
        self._moveArm(self.arm_home_value)
        self._moveActuator(self.actuator_up_value)
        self._vacuumOn(0)
        
    def lift(self):
        self._vacuumOn(True)
        print 'Robot\tlifting!'
        self.serialConnection.write("%s" % LOWER_AND_LIFT)
        self.clearSerialBuffers()
        last_height = 0
        for i in range(6):
            print 'Robot\titeration %s' % i
            resp = self.returnGadoInfo()
            try:
                print 'Robot\tresp: %s' % resp
                current_height = json.loads(resp)['actuator_pos_s']
                print 'Robot\tcurrent_height %s' % current_height
                if current_height == last_height:
                    return
            except:
                pass
            current_height = last_height
            time.sleep(1)
    
    #Move the actuator until the click sensor is engaged, then turn on the vacuum and raise
    #the actuator. The bulk of this code is going to be executed from the arduino's firmware
    def pickUpObject(self):
        print "Robot\tmoving arm to in pile"
        self._moveArm(self.arm_in_value)
        time.sleep(5)
        print 'Robot\tturning on vacuum'
        self.lift()
        print 'Robot\thopefully successfully picked up!'
        return True
    
    def scanObject(self):
        print 'Robot\tmoving to home value'
        self._moveArm(self.arm_home_value)
        time.sleep(5)
        print 'Robot\tdropping actuator'
        self._moveActuator(self.actuator_home_value)
        time.sleep(5)
        print 'Robot\tdone dropping on scanner??'
        print 'Robot\tturning off the pump'
        self._vacuumOn(False)
        return True
        
    def moveToOut(self):
        print 'Robot\tlifting actuator up'
        self._vacuumOn(True)
        self._moveActuator(self.actuator_up_value)
        time.sleep(5)
        print 'Robot\tmoving to out pile'
        self._moveArm(self.arm_out_value)
        time.sleep(5)
        self._vacuumOn(0)
        return True
    
    #Pause the robot in its current step
    def pause(self):
        print "Robot\tI'm paused inside the Robot object"
        pass
    
    #Stop the robot process and reset
    def stop(self):
        self._vacuumOn(0)
        self._moveActuator(self.actuator_up_value)
        pass
    
    '''#Reset all aspects of the robot
    def reset(self):
        self.resetArm()
        self.resetActuator()
    '''
    def in_pile(self):
        self.moveArm(self.arm_in_value)
    
    def listCommPorts(self):
        return self.serialConnection.tools.list_ports()