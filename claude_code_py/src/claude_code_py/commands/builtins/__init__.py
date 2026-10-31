"""Built-in slash commands."""

from claude_code_py.commands.builtins.add_dir import build_add_dir_command
from claude_code_py.commands.builtins.advisor import build_advisor_command
from claude_code_py.commands.builtins.agents import build_agents_command
from claude_code_py.commands.builtins.branch import build_branch_command
from claude_code_py.commands.builtins.btw import build_btw_command
from claude_code_py.commands.builtins.chrome import build_chrome_command
from claude_code_py.commands.builtins.clear import build_clear_command
from claude_code_py.commands.builtins.color import build_color_command
from claude_code_py.commands.builtins.compact import build_compact_command
from claude_code_py.commands.builtins.config import build_config_command
from claude_code_py.commands.builtins.context import build_context_command
from claude_code_py.commands.builtins.copy import build_copy_command
from claude_code_py.commands.builtins.cost import build_cost_command
from claude_code_py.commands.builtins.desktop import build_desktop_command
from claude_code_py.commands.builtins.diff import build_diff_command
from claude_code_py.commands.builtins.doctor import build_doctor_command
from claude_code_py.commands.builtins.effort import build_effort_command
from claude_code_py.commands.builtins.exit import build_exit_command
from claude_code_py.commands.builtins.export import build_export_command
from claude_code_py.commands.builtins.extra_usage import build_extra_usage_command
from claude_code_py.commands.builtins.fast import build_fast_command
from claude_code_py.commands.builtins.feedback import build_feedback_command
from claude_code_py.commands.builtins.files import build_files_command
from claude_code_py.commands.builtins.heapdump import build_heapdump_command
from claude_code_py.commands.builtins.help import build_help_command
from claude_code_py.commands.builtins.hooks import build_hooks_command
from claude_code_py.commands.builtins.ide import build_ide_command
from claude_code_py.commands.builtins.init import build_init_command
from claude_code_py.commands.builtins.insights import build_insights_command
from claude_code_py.commands.builtins.install_github_app import (
    build_install_github_app_command,
)
from claude_code_py.commands.builtins.install_slack_app import (
    build_install_slack_app_command,
)
from claude_code_py.commands.builtins.keybindings import build_keybindings_command
from claude_code_py.commands.builtins.login import build_login_command
from claude_code_py.commands.builtins.logout import build_logout_command
from claude_code_py.commands.builtins.mcp import build_mcp_command
from claude_code_py.commands.builtins.memory import build_memory_command
from claude_code_py.commands.builtins.mobile import build_mobile_command
from claude_code_py.commands.builtins.model import build_model_command
from claude_code_py.commands.builtins.output_style import build_output_style_command
from claude_code_py.commands.builtins.passes import build_passes_command
from claude_code_py.commands.builtins.permissions import build_permissions_command
from claude_code_py.commands.builtins.plan import build_plan_command
from claude_code_py.commands.builtins.plugin import build_plugin_command
from claude_code_py.commands.builtins.pr_comments import build_pr_comments_command
from claude_code_py.commands.builtins.privacy_settings import (
    build_privacy_settings_command,
)
from claude_code_py.commands.builtins.rate_limit_options import (
    build_rate_limit_options_command,
)
from claude_code_py.commands.builtins.release_notes import build_release_notes_command
from claude_code_py.commands.builtins.reload_plugins import build_reload_plugins_command
from claude_code_py.commands.builtins.remote_env import build_remote_env_command
from claude_code_py.commands.builtins.rename import build_rename_command
from claude_code_py.commands.builtins.resume import build_resume_command
from claude_code_py.commands.builtins.review import build_review_command
from claude_code_py.commands.builtins.rewind import build_rewind_command
from claude_code_py.commands.builtins.sandbox import build_sandbox_command
from claude_code_py.commands.builtins.security_review import (
    build_security_review_command,
)
from claude_code_py.commands.builtins.share import build_share_command
from claude_code_py.commands.builtins.session import build_session_command
from claude_code_py.commands.builtins.sessions import build_sessions_command
from claude_code_py.commands.builtins.skills import build_skills_command
from claude_code_py.commands.builtins.stats import build_stats_command
from claude_code_py.commands.builtins.status import build_status_command
from claude_code_py.commands.builtins.statusline import build_statusline_command
from claude_code_py.commands.builtins.stickers import build_stickers_command
from claude_code_py.commands.builtins.tag import build_tag_command
from claude_code_py.commands.builtins.tasks import build_tasks_command
from claude_code_py.commands.builtins.team import build_team_command
from claude_code_py.commands.builtins.terminal_setup import (
    build_terminal_setup_command,
)
from claude_code_py.commands.builtins.theme import build_theme_command
from claude_code_py.commands.builtins.think_back import build_think_back_command
from claude_code_py.commands.builtins.thinkback_play import (
    build_thinkback_play_command,
)
from claude_code_py.commands.builtins.ultrareview import build_ultrareview_command
from claude_code_py.commands.builtins.usage import build_usage_command
from claude_code_py.commands.builtins.upgrade import build_upgrade_command
from claude_code_py.commands.builtins.vim import build_vim_command
from claude_code_py.commands.builtins.voice import build_voice_command
from claude_code_py.commands.loader import SlashCommand


def build_builtin_commands() -> list[SlashCommand]:
    return [
        build_add_dir_command(),
        build_advisor_command(),
        build_agents_command(),
        build_branch_command(),
        build_btw_command(),
        build_chrome_command(),
        build_clear_command(),
        build_color_command(),
        build_compact_command(),
        build_config_command(),
        build_context_command(),
        build_copy_command(),
        build_cost_command(),
        build_desktop_command(),
        build_diff_command(),
        build_doctor_command(),
        build_effort_command(),
        build_exit_command(),
        build_export_command(),
        build_extra_usage_command(),
        build_fast_command(),
        build_feedback_command(),
        build_files_command(),
        build_heapdump_command(),
        build_help_command(),
        build_hooks_command(),
        build_ide_command(),
        build_init_command(),
        build_insights_command(),
        build_install_github_app_command(),
        build_install_slack_app_command(),
        build_keybindings_command(),
        build_login_command(),
        build_logout_command(),
        build_mcp_command(),
        build_memory_command(),
        build_mobile_command(),
        build_model_command(),
        build_output_style_command(),
        build_passes_command(),
        build_permissions_command(),
        build_plan_command(),
        build_plugin_command(),
        build_pr_comments_command(),
        build_privacy_settings_command(),
        build_rate_limit_options_command(),
        build_release_notes_command(),
        build_reload_plugins_command(),
        build_remote_env_command(),
        build_rename_command(),
        build_resume_command(),
        build_review_command(),
        build_rewind_command(),
        build_sandbox_command(),
        build_security_review_command(),
        build_share_command(),
        build_session_command(),
        build_sessions_command(),
        build_skills_command(),
        build_stats_command(),
        build_status_command(),
        build_statusline_command(),
        build_stickers_command(),
        build_tag_command(),
        build_tasks_command(),
        build_team_command(),
        build_terminal_setup_command(),
        build_theme_command(),
        build_think_back_command(),
        build_thinkback_play_command(),
        build_ultrareview_command(),
        build_upgrade_command(),
        build_usage_command(),
        build_vim_command(),
        build_voice_command(),
    ]
