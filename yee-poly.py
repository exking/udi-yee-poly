#!/usr/bin/env python3

import polyinterface
import sys
import json
from yeelight import discover_bulbs, Bulb, RGBTransition, SleepTransition, Flow, BulbException
from yeelight.transitions import disco, temp, strobe, pulse, strobe_color, alarm, police, police2, christmas, rgb, randomloop, lsd, slowdown

LOGGER = polyinterface.LOGGER

DEF_BRMAX = 100
DEF_BRMIN = 1
DEF_DURATION = 300
DEF_MIN_DURATION = 30
DEF_INCREMENT = 4
FADE_TRANSTIME = 4000
EFFECT_MAP = [ disco, temp, strobe, strobe_color, alarm, police, police2, christmas, rgb, randomloop, lsd, slowdown ]

""" Common color names and their RGB values. """
colors = {
    0: ['aqua', [127, 255, 212]],
    1: ['azure', [0, 127, 255]],
    2: ['beige', [245, 245, 220]],
    3: ['blue', [0, 0, 255]],
    4: ['chartreuse', [127, 255, 0]],
    5: ['coral', [0, 63, 72]],
    6: ['crimson', [220, 20, 60]],
    7: ['forest green', [34, 139, 34]],
    8: ['fuchsia', [255, 119, 255]],
    9: ['golden', [255, 215, 0]],
    10: ['gray', [128, 128, 128]],
    11: ['green', [0, 255, 0]],
    12: ['hot pink', [252, 15, 192]],
    13: ['indigo', [75, 0, 130]],
    14: ['lavender', [181, 126, 220]],
    15: ['lime', [191, 255, 0]],
    16: ['maroon', [128, 0, 0]],
    17: ['navy blue', [0, 0, 128]],
    18: ['olive', [128, 128, 0]],
    19: ['red', [255, 0, 0]],
    20: ['royal blue', [8, 76, 158]],
    21: ['tan', [210, 180, 140]],
    22: ['teal', [0, 128, 128]],
    23: ['white', [255, 255, 255]]
 }


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'Yeelight Controller'
        self.address = 'yeectrl'
        self.primary = self.address
        self.devlist = None

    def start(self):
        # LOGGER.setLevel(logging.INFO)
        LOGGER.info('Started Yeelight controller')
        if 'devlist' in self.polyConfig['customParams']:
            try:
                self.devlist = json.loads(self.polyConfig['customParams']['devlist'])
            except Exception as ex:
                LOGGER.error('Failed to parse the devlist: {}'.format(ex))
                return False
        self.discover()

    def stop(self):
        LOGGER.info('Yeelight is stopping')

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def shortPoll(self):
        self.updateNodes()

    def updateNodes(self):
        for node in self.nodes:
            self.nodes[node].updateInfo()

    def updateInfo(self):
        pass

    def discover(self, command=None):
        if self.devlist:
            LOGGER.info("Using manually specified device list")
            for bulb_info in self.devlist:
                LOGGER.debug(bulb_info)
                address = bulb_info['address'][:14]
                bulb = Bulb(bulb_info['ip'])
                bulb_properties = bulb.get_properties()
                name = bulb_info['name']
                if name is None:
                    name = 'YeeLight ' + address[10:14]
                if not address in self.nodes:
                    LOGGER.info('Adding YeeLight bulb id: {}, name: {}'.format(address, name))
                    self.addNode(YeeColorBulb(self, self.address, address, name, bulb))
        else:
            for bulb_info in discover_bulbs():
                LOGGER.debug(bulb_info)
                address = str(bulb_info['capabilities']['id'])[-14:]
                bulb = Bulb(bulb_info['ip'])
                bulb_properties = bulb.get_properties()
                name = bulb_properties['name']
                if name is None:
                    name = 'YeeLight ' + address[10:14]
                if not address in self.nodes:
                    LOGGER.info('Adding YeeLight bulb id: {}, name: {}'.format(bulb_info['capabilities']['id'], name))
                    self.addNode(YeeColorBulb(self, self.address, address, name, bulb))

    id = 'YEECTRL'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2}]


class YeeColorBulb(polyinterface.Node):
    def __init__(self, controller, primary, address, name, bulb):
        super().__init__(controller, primary, address, name)
        self.bulb = bulb
        self.power = False
        self.bulb_properties = None
        self.duration = DEF_DURATION
        self.bri = DEF_BRMAX
        self.hue = 0
        self.sat = DEF_BRMAX

    def start(self):
        LOGGER.info('Starting bulb {}'.format(self.name))
        try:
            self.duration = int(self.getDriver('RR'))
        except:
            self.duration = DEF_DURATION
        self.updateInfo()

    def updateInfo(self):
        try:
            self.bulb_properties = self.bulb.get_properties()
        except Exception as ex:
            LOGGER.error('Unable to get {} properties'.format(self.name, ex))
            return
        if self.bulb_properties['power'] == 'on':
            if self.power is False:
                self.reportCmd('DON')
            self.power = True
            self.setDriver('ST', int(self.bulb_properties['bright']))
        else:
            if self.power:
                self.reportCmd('DOF')
            self.power = False
            self.setDriver('ST', 0)
        self.setDriver('GPV', int(self.bulb_properties['color_mode']))
        self.setDriver('CLITEMP', int(self.bulb_properties['ct']))
        self.hue = int(self.bulb_properties['hue'])
        self.sat = int(self.bulb_properties['sat'])
        self.bri = int(self.bulb_properties['bright'])
        self.setDriver('GV0', self.hue)
        self.setDriver('GV1', self.sat)
        self.setDriver('GV2', self.bri)
        if self.bulb_properties['music_on'] == 'on':
            self.setDriver('GV6', 1)
        else:
            self.setDriver('GV6', 0)
        rgb = int(self.bulb_properties['rgb'])
        blue = rgb & 0xff
        green = (rgb >> 8) & 0xff
        red = (rgb >> 16) & 0xff
        self.setDriver('GV3', red)
        self.setDriver('GV4', green)
        self.setDriver('GV5', blue)
        self.setDriver('RR', self.duration)
        
    def query(self):
        self.reportDrivers()

    def set_on(self, command):
        new_bri = None
        cmd = command.get('cmd')
        val = command.get('value')
        if val:
            ''' we will be adjusting brightness as well'''
            new_bri = int(val)
        if cmd == 'DFON':
            trans = DEF_MIN_DURATION
            new_bri = DEF_BRMAX
        else:
            trans = self.duration
        try:
            self.bulb.turn_on(duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to turn on {}'.format(self.name, ex))
            return
        self.power = True
        if new_bri and self.bri != new_bri:
            self.bri = new_bri
            try:
                self.bulb.set_brightness(self.bri, duration=trans)
            except Exception as ex:
                LOGGER.error('Bulb {} failed to set brightness {}'.format(self.name, ex))
            self.setDriver('GV2', self.bri)
        self.setDriver('ST', self.bri)

    def set_off(self, command):
        cmd = command.get('cmd')
        if cmd == 'DFOF':
            trans = DEF_MIN_DURATION
        else:
            trans = self.duration
        try:
            self.bulb.turn_off(duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to turn off {}'.format(self.name, ex))
            return
        self.setDriver('ST', 0)
        self.power = False

    def _power_on(self, trans=None):
        if trans is None:
            trans = self.duration
        if not self.power:
            try:
                self.bulb.turn_on(duration=trans)
            except Exception as ax:
                LOGGER.error('Bulb {} failed to turn on {}'.format(self.name, ex))
                return
            self.power = True
            self.setDriver('ST', int(self.bulb_properties['bright']))

    def set_transition(self, command):
        self.duration = int(command.get('value'))
        self.setDriver('RR', self.duration)

    def set_colortemp(self, command):
        new_bri = None
        trans = self.duration
        cmd = command.get('cmd')
        if cmd == 'SET_CTBR':
            query = command.get('query')
            ct = int(query.get('K.uom26'))
            new_bri = int(query.get('BR.uom100'))
            trans = int(query.get('D.uom42'))
        else:
            ct = int(command.get('value'))
        self._power_on(trans=DEF_MIN_DURATION)
        try:
            self.bulb.set_color_temp(ct, duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set color temperature {}'.format(self.name, ex))
            return
        if new_bri:
            self.bri = new_bri
            try:
                self.bulb.set_brightness(self.bri, duration=trans)
            except Exception as ex:
                LOGGER.error('Bulb {} failed to set color temperature {}'.format(self.name, ex))
                return
            self.setDriver('GV2', self.bri)
            self.setDriver('ST', self.bri)
        self.setDriver('CLITEMP', ct)

    def set_rgb(self, command):
        query = command.get('query')
        color_r = int(query.get('R.uom100'))
        color_g = int(query.get('G.uom100'))
        color_b = int(query.get('B.uom100'))
        trans = int(query.get('D.uom42'))
        self._power_on(trans=DEF_MIN_DURATION)
        try:
            self.bulb.set_rgb(color_r, color_g, color_b, duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set RGB color{}'.format(self.name, ex))
            return
        self.setDriver('GV3', color_r)
        self.setDriver('GV4', color_g)
        self.setDriver('GV5', color_b)

    def set_color(self, command):
        color_id = int(command.get('value'))
        (color_r, color_g, color_b) = colors[color_id][1]
        self._power_on(trans=DEF_MIN_DURATION)
        try:
            self.bulb.set_rgb(color_r, color_g, color_b, duration=self.duration)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set RGB color{}'.format(self.name, ex))
            return
        self.setDriver('GV3', color_r)
        self.setDriver('GV4', color_g)
        self.setDriver('GV5', color_b)

    def set_hsv(self, command):
        cmd = command.get('cmd')
        trans = self.duration
        self._power_on(trans=DEF_MIN_DURATION)
        if cmd == 'SET_HSB':
            query = command.get('query')
            self.hue = int(query.get('H.uom56'))
            self.sat = int(query.get('S.uom100'))
            self.bri = int(query.get('BR.uom100'))
            trans = int(query.get('D.uom42'))
        elif cmd == 'SET_HUE':
            self.hue = int(command.get('value'))
        elif cmd == 'SET_SAT':
            self.sat = int(command.get('value'))
        elif cmd == 'SET_BRI':
            ''' special case here, we need to use set_brightness as in color temperature mode bulb does not update HSV '''
            self.bri = int(command.get('value'))
            try:
                self.bulb.set_brightness(self.bri, duration=trans)
            except Exception as ex:
                LOGGER.error('Bulb {} failed to set brightness {}'.format(self.name, ex))
                return
            self.setDriver('GV2', self.bri)
            self.setDriver('ST', self.bri)
            return
        else:
            LOGGER.error('Unknown command {} to set_hsv'.format(cmd))
            return
        try:
            self.bulb.set_hsv(self.hue, self.sat, self.bri, duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set HSV color {}'.format(self.name, ex))
            return
        self.setDriver('GV0', self.hue)
        self.setDriver('GV1', self.sat)
        self.setDriver('GV2', self.bri)
        self.setDriver('ST', self.bri)

    def brt_dim(self, command):
        cmd = command.get('cmd')
        if cmd == 'BRT':
            if not self.power:
                self._power_on(trans=DEF_MIN_DURATION)
            new_bri = self.bri + DEF_INCREMENT
        elif cmd == 'DIM':
            new_bri = self.bri - DEF_INCREMENT
        if new_bri < DEF_BRMIN:
            new_bri = DEF_BRMIN
        elif new_bri > DEF_BRMAX:
            new_bri = DEF_BRMAX
        if new_bri == self.bri:
            LOGGER.error('{} can\'t {}, brightness is currently {}'.format(self.name, cmd, self.bri))
            return
        self.bri = new_bri
        try:
            self.bulb.set_brightness(self.bri, duration=self.duration)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set brightness {}'.format(self.name, ex))
            return
        self.setDriver('GV2', self.bri)
        self.setDriver('ST', self.bri)

    def fade(self, command):
        cmd = command.get('cmd')
        trans = FADE_TRANSTIME
        if not self.power:
            if cmd != 'FDUP':
                LOGGER.error('{} is OFF, can\'t {}'.format(self.name, cmd))
                return
            self._power_on(trans=DEF_MIN_DURATION)
        if cmd == 'FDUP':
            new_bri = DEF_BRMAX
        elif cmd == 'FDDOWN':
            new_bri = DEF_BRMIN
        elif cmd == 'FDSTOP':
            self.updateInfo()
            new_bri = self.bri
            trans = DEF_MIN_DURATION
        else:
            LOGGER.error('Invalid command {} to fade'.format(cmd))
            return
        self.bri = new_bri
        try:
            self.bulb.set_brightness(self.bri, duration=trans)
        except Exception as ex:
            LOGGER.error('Bulb {} failed to set brightness {}'.format(self.name, ex))
            return
        self.setDriver('GV2', self.bri)
        self.setDriver('ST', self.bri)

    def set_effect(self, command):
        val = int(command.get('value'))
        if val < 0 or val > 12:
            LOGGER.error('Invalid effect number {}'.format(val))
            return
        if val > 0:
            LOGGER.debug('{} starting effect {}'.format(self.name, val-1))
        if not self.power:
            if val == 0:
                LOGGER.error('{} is off, can\'t stop the effect'.format(self.name))
            self._power_on()
        if val == 0:
            LOGGER.info('{} stopping effect'.format(self.name))
            try:
                self.bulb.stop_flow()
            except Exception as ex:
                LOGGER.error('{} failed to stop effect {}'.format(self.name, ex))
            return
        flow = Flow(count=0, transitions=EFFECT_MAP[val-1]())
        try:
            self.bulb.start_flow(flow)
        except Exception as ex:
            LOGGER.error('{} failed to start effect {}'.format(self.name, ex))


    drivers = [{'driver': 'ST', 'value': 0, 'uom': 51},
               {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
               {'driver': 'RR', 'value': DEF_DURATION, 'uom': 42},
               {'driver': 'GPV', 'value': 0, 'uom': 25},
               {'driver': 'GV0', 'value': 0, 'uom': 56},
               {'driver': 'GV1', 'value': 0, 'uom': 100},
               {'driver': 'GV2', 'value': 0, 'uom': 100},
               {'driver': 'GV3', 'value': 0, 'uom': 100},
               {'driver': 'GV4', 'value': 0, 'uom': 100},
               {'driver': 'GV5', 'value': 0, 'uom': 100},
               {'driver': 'GV6', 'value': 0, 'uom': 2},
              ]

    id = 'YEEBULB'

    commands = {
            'QUERY': query, 'DON': set_on, 'DOF': set_off, 'DFON': set_on, 'DFOF': set_off, 'RR': set_transition, 'CLITEMP': set_colortemp, 'SET_COLOR_RGB': set_rgb,
            'SET_COLOR': set_color, 'SET_HSB': set_hsv, 'SET_CTBR': set_colortemp, 'SET_HUE': set_hsv, 'SET_SAT': set_hsv, 'SET_BRI': set_hsv, 'BRT': brt_dim, 'DIM': brt_dim,
            'FDUP': fade, 'FDDOWN': fade, 'FDSTOP': fade, 'EFFECT': set_effect
               }


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Yeelight')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
