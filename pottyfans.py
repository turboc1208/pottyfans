##########################################################
# PottyFans
# Written by Chip Cox
# Date 05FEB2017
#
# Revision History
# 05FEB2017 Chip Cox  First complete version
#
# allow for multiple lights to control a fan and each other like in sam's bathroom
# outter light and inside light controlling inside fan
##########################
#
# appdaemon.cfg file
# [pottyfans]
# module=pottyfans
# class=pottyfans
# masterGroup=HA Group Name that contains groups of toilet room light/fan pairs
# delay=300  - optional
##########################################################
import appdaemon.appapi as appapi
import inspect
             
class pottyfans(appapi.AppDaemon):

  def initialize(self):
    self.log("Initializing pottyfans")
    self.mainGroup=self.args["masterGroup"]   # get name of HA group from config file
    if "delay" in self.args:
      self.delay=self.args["delay"]           # get delay value from config file
    else:
      self.delay=300                          # default delay to 5 minutes if not in config file
    self.log("mainGroup={}, delay={}".format(self.mainGroup,self.delay))
    self.fanpairs={}
    self.fanpairs=self.build_member_list(self.mainGroup)  # convert HA group onto internal dictionary
    #self.log("fanpairs={}".format(self.fanpairs))
    for i in self.fanpairs:                   # run through dictionary an register callbacks
      self.listen_state(self.light_change,entity=i["switch"])
      self.log("registered {}".format(i["switch"]))
      self.listen_state(self.fan_on,entity=i["fan"],old='off',new='on') 
      self.log("registered {}".format(i["fan"]))

  #############
  #
  # Search fanpairs dictionary for the toilet where the given light exists
  #############
  def findLight(self,entity):
    rval=None
    for room in self.fanpairs:
      if room["switch"]==entity:
        rval=room
    return(rval)
  
  #############
  #
  # Search fanpairs dictionary for the toilet where the given fan exists
  #############
  def findFan(self,entity):
    rval=None
    for room in self.fanpairs:
      if room["fan"]==entity:
        rval=room
    return(rval)

  #############
  #
  # Callback when lights are turned off
  #############
  def light_change(self,entity,attribute,old,new,kwargs):
    toilet=self.findLight(entity)    # get the correct toilet room
    if not old==new:
      if new=="off":
        if not toilet==None:
          self.log("entity {} in toilet".format(toilet["switch"]))
          self.run_in(self.turnoff_fan,self.delay,fan=toilet["fan"])    # register timer to turn off fan
          self.log("will turn off fan {} in {} minutes".format(toilet["fan"],int(self.delay/60)))
        else:
          self.log("entity {} not in toilet".format(entity))
      else:
        self.run_in(self.check_light_on,300,light=entity)

  def check_light_on(self,kwargs):
    self.log("light={}".format(kwargs))
    if kwargs["light"]=="":
      self.log("light not specified")
    else:
      if self.get_state(kwargs["light"])=="on":
        light=kwargs["light"]
        self.log("light={}".format(light))
        room=self.findLight(light)
        self.log("room={}".format(room))
        fan=room["fan"]
        self.log("fan={}".format(fan))
        self.turn_on(fan)  

  #############
  #
  # Callback when fans are turned off
  #############
  def fan_on(self,entity,attribute,old,new,kwargs):
    toilet=self.findFan(entity)
    if not toilet==None:
      self.log("{} findFan returned {}".format(entity,toilet))
      if not self.get_state(toilet["switch"])=='on':      # if the light is not turned on register event to turn off fan
        self.log("light {} is not on, scheduling fan {} to turn off in {} minutes".format(
                 toilet["switch"],toilet["fan"],int(self.delay/60)))
        self.run_in(self.turnoff_fan,self.delay,fan=toilet["fan"])
        self.log("Will turn off fan {} in {} minutes".format(toilet["fan"],int(self.delay/60)))

  #############
  #
  # Callback from timer to actually turn the fan off
  #############
  def turnoff_fan(self,kwargs):
    toilet=self.findFan(kwargs["fan"])
    if self.get_state(toilet["switch"])=="off":            # if the light is off turn off the fan
      self.log("turning off {}".format(kwargs['fan']))
      self.turn_off(toilet['fan'])
    else:                                                  # if the light is on, let the fan keep running
      self.log("{} is on so not turning off {}".format(toilet["switch"],toilet["fan"]))

  #############
  #
  # loop through the group that was passed in as entity and return a dictionary of entities
  #############
  def build_member_list(self,entity):
    elist=[]
    for object in self.get_state(entity,attribute='all')["attributes"]["entity_id"]:
      #self.log("object={}".format(object))
      device, entity = self.split_entity(object)
      if device=="group":
        fan=""
        switch=""
        for e in self.get_state(object,attribute='all')["attributes"]["entity_id"]:
          if e.find("fan")>=0:
            fan=e
          else:
            switch=e
          if not ((fan=="") or (switch=="")):         # we have a fan and a switch
            elist.append({"switch":switch,"fan":fan}) # add this toilet to the list
      #self.log("elist={}".format(elist),level="INFO")
    return(elist)

  #############
  #
  # Override of normal log to force in function and line number with message
  #############
  def log(self,msg,level="INFO"):
    obj,fname, line, func, context, index=inspect.getouterframes(inspect.currentframe())[1]
    super(pottyfans,self).log("{} - ({}) {}".format(func,str(line),msg),level)

