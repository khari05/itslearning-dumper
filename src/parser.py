import argparse


def makeParser():
    parser = argparse.ArgumentParser(
        description='Download files from itslearning. Check the README for more information.')

    parser.add_argument('--output-dir', '-O', dest='output_dir', default=None,
                        help='Defines the directory to output files from. If left empty, the program will prompt.')
    parser.add_argument('--rate-limit-delay', '-R', dest='rate_limit', type=float, default=1,
                        help="Rate limits requests to It's Learning (seconds). Defaults to 1 second.")
    parser.add_argument('--skip-to-course', '-S', dest='skip_to_course', type=int, default=0,
                        help='Skip to a course with a specific index. Useful after a crash. Set to 1 to only skip downloading internal messages.')
    parser.add_argument('--enable-checkpoints', '-C', dest='enable_checkpoints', type=bool, default=False,
                        help='Save the location of the last element encountered by the dumping process. Useful for quick recovery while debugging, or being able to continue the dumping process at a later date.')
    parser.add_argument('--output-text-extension', '-E', dest='output_extension', default='.html',
                        help='Specifies the extension given to produced plaintext files. Values ought to be either ".html" or ".txt".')
    parser.add_argument('--institution', '-I', dest='institution', default=None,
                        help='Only dump the content of a single institution site. This value should either be "ntnu" or "hist".')
    parser.add_argument('--list', '-L', dest='do_listing', action='store_true',
                        help='Don\'t dump anything, just list all courses and projects for each institution, along with their IDs.')
    parser.add_argument('--projects-only', '-P', dest='projects_only', action='store_true',
                        help='Only dump projects. No internal messages or courses are saved.')
    parser.add_argument('--courses-only', '-F', dest='courses_only', action='store_true',
                        help='Only dump courses. No internal messages or projects are saved.')
    parser.add_argument('--messages-only', '-M', dest='messaging_only', action='store_true',
                        help='Only dump internal messages. No courses or projects are saved.')
    parser.add_argument('--recreate-dump-dir', '-D', dest='recreate_out_dir', action='store_true',
                        help='Delete the output directory and recreate it (useful for debugging)')
    parser.add_argument('--username', '-U', dest='username', default=None,
                        help='Specify a username to be dumped')
    parser.add_argument('--password', '-Q', dest='password', default=None,
                        help='Specify a password of the user to be dumped')

    return parser
