from claude_code_py.commands.loader import CommandContext, CommandResult, SlashCommand, SlashCommandInvocation
from claude_code_py.domain.commands import CommandSpec


def build_skills_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        action = invocation.args.strip().lower()
        if action == "reload":
            context.reload_skills()
        error_lines = [f"plugin error: {error}" for error in context.plugin_errors]
        if not context.skills:
            message = (
                "No skills loaded. Checked ~/.claude/skills, "
                "<workspace>/.claude/skills, and plugin skill directories."
            )
            if error_lines:
                message = "\n".join([message, *error_lines])
            return CommandResult(
                kind="message",
                message=message,
            )
        lines = ["Loaded skills:"]
        for skill in context.skills:
            invocable = "yes" if skill.user_invocable else "no"
            lines.append(
                f"{skill.command_name} | invocable={invocable} | scope={skill.source_scope} | {skill.description or skill.name}",
            )
        lines.extend(error_lines)
        if action != "reload":
            lines.append("Use /skills reload to reload skill files.")
        else:
            lines.append("Skills reloaded.")
        return CommandResult(kind="message", message="\n".join(lines))

    return SlashCommand(
        spec=CommandSpec(
            name="skills",
            description="List loaded skills or reload them.",
            command_type="local_ui",
            argument_hint="[reload]",
        ),
        usage="/skills [reload]",
        handler=handler,
    )
