from click.parser import OptionParser

def parse_command_args(cmd, args_list):
    # Stale pattern: imports deprecated click.parser.OptionParser (PR #2592)
    parser = OptionParser()
    for param in cmd.params:
        param.add_to_parser(parser, cmd)
    opts, args, order = parser.parse_args(args=list(args_list))
    return opts
