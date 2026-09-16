import click

def parse_command_args(cmd, args_list):
    # Valid pattern: uses cmd.make_context params
    ctx = cmd.make_context(cmd.name, list(args_list))
    return ctx.params
