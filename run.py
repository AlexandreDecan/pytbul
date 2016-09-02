import sys
from pytbul.gui import main


if __name__ == '__main__':
    argv = sys.argv

    #if '-style' not in argv:
    #    argv.append('-style')
    #    argv.append('adwaita')

    main(argv)

