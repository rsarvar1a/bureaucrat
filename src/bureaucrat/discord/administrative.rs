
use super::prelude::*;

pub fn register() -> Vec<Command>
{
    vec![
        setup(),
        setup_owner()
    ]
}

/// Register Bureaucrat's commands so they work in your server
#[command(
    prefix_command,
    category = "Administrative",
    required_permissions = "MANAGE_GUILD"
)]
async fn setup(ctx: Context<'_>) -> Result
{
    poise::builtins::register_in_guild(ctx, & ctx.framework().options.commands, ctx.guild_id().unwrap()).await?;
    Ok(())
}

/// Open Bureaucrat's command registration menu
#[command(
    prefix_command, 
    hide_in_help,
    owners_only
)]
async fn setup_owner(ctx: Context<'_>) -> Result
{
    poise::builtins::register_application_commands_buttons(ctx).await?;
    Ok(())
}
