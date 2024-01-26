
use super::{prelude::{self, *}, utils};

mod submit;

/// Returns the commands provided by this module.
pub fn register() -> Vec<Command>
{
    vec![
        feedback(),
    ]
}

/// Interact with Storyteller feedback
#[command(
    prefix_command, slash_command, 
    category = "Feedback",
    subcommands(
        "submit::submit"
    )
)]
async fn feedback(ctx: Context<'_>) -> Result
{
    ctx.say("Use this submodule to interact with Storyteller feedback.").await?;
    Ok(())
}
