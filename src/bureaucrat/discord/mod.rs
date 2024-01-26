// Framework setup.

/// Re-exports useful poise and serenity items for use in bot development.
mod prelude
{
    pub use crate::bureaucrat::configuration::*;
    pub use crate::bureaucrat::services::Services;

    pub use poise::serenity_prelude as serenity;
    pub use poise::{self, command};

    // Important types.

    pub type Command = poise::Command<Services, Error>;
    pub type Context<'a> = poise::Context<'a, Services, Error>;
    pub type Error = anyhow::Error;
    pub type Result = anyhow::Result<(), Error>;
}

use prelude::*;
use anyhow::{Context, Error, Result};

// Command groups as modules that register into the global application framework.

mod administrative;
mod feedback;
mod misc;
mod utils;

// Exports.

/// Creates a Discord client.
pub async fn create_client() -> Result<serenity::Client, Error>
{
    let cfg = Configuration::get().discord;

    let commands = vec![
        administrative::register(),
        feedback::register(),
        misc::register()
    ]
        .into_iter().flatten()
        .collect::<Vec<Command>>();

    let framework = poise::Framework::<Services, Error>::builder()
        .options(poise::FrameworkOptions {
            commands,
            prefix_options: poise::PrefixFrameworkOptions {
                prefix: Some(cfg.prefix),
                ..Default::default()
            },
            ..Default::default()
        })
        .setup(move |_, _, _| {
            Box::pin(async move {
                Ok(Services::default())
            })
        })
        .build();

    let intents =
        serenity::GatewayIntents::non_privileged() | serenity::GatewayIntents::MESSAGE_CONTENT;

    let client = serenity::ClientBuilder::new(cfg.token, intents)
        .framework(framework)
        .await
        .context("failed to construct client")?;

    Ok(client)
}
