#! /usr/bin/python
# Runs MoodMusic
# Usage: ./test_cli.py path/to/song.mp3

from ui.cli import *
from song.song import Song
#import myconfig

from input.Import import FetchData

def run(songPath):
    
    # start a daemon in background to fetch song data
    # @todo: we can do this with multiple threads for speed up 
    daemon = FetchData()
    daemon.start()
    
    #Start CLI
    application = CLI()
    mySong = Song.song_from_filepath(songPath)
    application.play_song(mySong)

if __name__ == '__main__':
    # the only argument to this file is either -h/--help or the file path
    # if its not help, run the application
    if sys.argv[1:] and sys.argv[1] not in ('-h', '--help'):
        run(sys.argv[1])

    else: # print the help message
        print('Usage: %s <song_filename>' % sys.argv[0])
        print('Once launched, type ? for the menu.\n')
        