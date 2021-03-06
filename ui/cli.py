#! /usr/bin/python
# Author: Brian Kracoff
# A command-line interface using vlc's engine
# To use, create a new CLI object and use cliObject.play_song(fileName)

from libraries.vlc import *
import ctypes
from ctypes.util import find_library
import os
import sys
from collections import OrderedDict
from inspect import getargspec
from song.song import *
from config import Config
from search.songSearch import *

try:
    from msvcrt import getch
except ImportError:
    import termios
    import tty

class CLI:
    def __init__(self, daemon=None):
        self.daemon = daemon
        self.echo_position = False
        self.instance = Instance("--sub-source marq")

        self.playlist = None        

    def set_list(self, p):
        self.playlist = p

    def print_daemon_info(self):
        """Print status about the song importer"""
        print('Songs imported: %i' % self.daemon.process['done'])

    def pos_callback(self, event):
        if self.echo_position:
            sys.stdout.write('\rPosition in song: %.2f%%' % (self.player.get_position() * 100))
            sys.stdout.flush()

    def print_info(self):
        """Print information about the media"""
        try:
            media = self.player.get_media()
            print('State: %s' % self.player.get_state())
            print('Media: %s' % bytes_to_str(media.get_mrl()))
            print('Current time: %s/%s' % (self.player.get_time(), media.get_duration()))
            print('Position: %s' % self.player.get_position())
            
            #Print attributes
            for key, value in self.song.get_attr().iteritems():
                print('%s: %s' % (key, value))

        except Exception:
            print('Error: %s' % sys.exc_info()[1])

    def print_menu(self):
        """Print menu"""
        print('Single-character commands:')
        for k, m in self.keybindings.items():
            if(k != '?'):
                m = (m.__doc__ or m.__name__).splitlines()[0]
                print('  %s -> %s.' % (k, m.rstrip('.')))
        print('0-9: go to that fraction of the movie')

    #Toggles whether the current position of the song should be shown
    def toggle_echo_position(self):
        """Toggle echoing of media position"""
        self.echo_position = not self.echo_position

    #Navigates to the portion of the song desired
    #portion - must be a single digit, 0 through 9
    def jump_to_position(self, portion):
        if portion.isdigit():
            self.player.set_position(float('0.'+portion))

    #Go to next track in playlist
    def next_track(self):
        """Go to next track in playlist"""
        self.play_song(self.nextSongPath)

    #Open a new track to play
    def play_different_track(self):
        """Play a different track"""
        
        print "\nHow would you like to select a song?\n"
        print "l -> Search your Library"
        print "f -> Enter a filepath"

        selection = raw_input('> ')
        while (selection not in ['l', 'f']):
            selection = raw_input('Please enter an option above: ')
        if selection == 'l':
            filePath = song_search(Config().get_attr('MUSIC_LIBRARY_FILE_PATH'))
        elif selection == 'f':
            #User enters a filepath
            filePath = raw_input('Enter a file path to a new song: ')

        if filePath != None:
        
            song = Song.song_from_filepath(filePath)
            self.playlist = None
            self.play_song(song)
        
    #Add the current track to a user-inputted mood
    def add_to_mood(self):
        """Add track to one of your moods"""

        print('Moods that song is a part of:\n')
        for mood in self.song.get_moods():
            print('  %s' % mood)

        moods = DB_Helper().all_moods()

        print('\nAdd to another mood:\n')
        index = 0
        for mood in moods:
            if mood not in self.song.get_moods():
                print('  %i -> %s' % (index, mood))
                index += 1
        print('  n -> new mood')
        print('  -1 -> cancel')

        moodIndex = raw_input('\nEnter choice: ')

        if moodIndex == 'n':
            #Create new mood and add song to it
            chosenMood = raw_input('Enter new mood name: ')
        else:
            try:
                moodIndex = int(float(moodIndex))
            except Exception:
                #Simply returns if user doesn't enter a correct input
                print('Cancelled...')
                return

            if moodIndex < 0 or moodIndex >= len(moods):
                #User chose to not add song to a mood or didn't enter a correct number
                print('Cancelled...')
                return
            else:
                #Add song to one of the current moods
                chosenMood = moods[moodIndex]

        self.song.add_mood(chosenMood)
        print('Added song to \'%s\'' % chosenMood)


    #Called in separate thread when song ends
    def end_callback(self, event):
        print("End of song. Please type a new command (\'>\' for next song in playlist or \'n\' to enter a new song)")

    def quit_app(self):
        """Stop and exit"""
        sys.exit(0)

    def play_song(self, song=None):
        if song == None and self.playlist == None:
            print "Need a playlist or a song."
            sys.exit(1)
        elif song == None:
            if self.playlist.has_next_song():
                self.song = self.playlist.get_current_song()
            else: 
                print ("\nThere are no songs in your database associated with that mood\n"
                       "-- make sure any songs you assigned to that mood are in your database\n")
                return
        else:
            self.song = song

        if self.playlist:
            if self.playlist.has_next_song():
                self.nextSongPath = self.playlist.get_next_song()
            else:
                self.playlist._currentI = -1
                self.nextSongPath = self.playlist.get_next_song()

        try:
            media = self.instance.media_new(self.song.file)
        except NameError:
            print('NameError: %s (%s vs LibVLC %s)' % (sys.exc_info()[1], __version__, libvlc_get_version()))
            sys.exit(1)

        #Starts playing media
        if hasattr(self, 'player'):
            self.player.stop()
        self.player = self.instance.media_player_new()
        event_manager = self.player.event_manager()
        event_manager.event_attach(EventType.MediaPlayerEndReached,      self.end_callback)
        event_manager.event_attach(EventType.MediaPlayerPositionChanged, self.pos_callback)
        self.player.set_media(media)
        self.player.play()

        #Constant keybindings for menu
        self.keybindings = OrderedDict()
        self.keybindings.setdefault(' ', self.player.pause)
        self.keybindings.setdefault('m', self.add_to_mood)
        self.keybindings.setdefault('i', self.print_info)
        if self.daemon:
            self.keybindings.setdefault('d', self.print_daemon_info)
        self.keybindings.setdefault('p', self.toggle_echo_position)
        self.keybindings.setdefault('n', self.play_different_track)
        if self.playlist:
            self.keybindings.setdefault('>', self.next_track)
        self.keybindings.setdefault('q', self.quit_app)
        self.keybindings.setdefault('?', self.print_menu)

        print('***********************')
        print('Now playing: %s' % bytes_to_str(media.get_mrl()))
        print('Moods: %s' % self.song.get_moods())
        print('Press q to quit, ? to see menu.')
        print('***********************')

        #Main loop of program, continues until user quits
        while True:
            k = getch()
            print('> %s' % k)
            if k in self.keybindings:
                self.keybindings[k]()
            elif k.isdigit():
                # jump to fraction of the song.
                self.jump_to_position(k)

#Listens for a 1 character input from the user
def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

