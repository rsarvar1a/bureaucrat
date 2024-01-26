
use super::prelude::*;

/// Returns the commands provided by this module.
pub fn register() -> Vec<Command>
{
    vec![
        hello(),
        help()
    ]
}

/// Say hello
#[command(
    slash_command, prefix_command,
    category = "Miscellaneous"
)]
async fn hello(ctx: Context<'_>) -> Result
{
    ctx.reply(
        format!(
            "Hi {}, I'm {}!", 
            ctx.author().to_string(), 
            Configuration::get().server.name
        )
    ).await?;
    
    Ok(())
}

/// Show this help menu
#[command(
    slash_command, prefix_command,
    category = "Miscellaneous"
)]
async fn help(ctx: Context<'_>, command: Option<String>) -> Result 
{
    let configuration = poise::builtins::HelpConfiguration 
    {
        show_subcommands: true,
        ..Default::default()
    };

    poise::builtins::help(ctx, command.as_deref(), configuration).await?;
    Ok(())
}
