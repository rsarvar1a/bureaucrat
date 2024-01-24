use crate::bureaucrat::{Configuration, Services};

use anyhow::{Context, Error, Result};
use poise::serenity_prelude as serenity;

// Serenity client frontend.

pub async fn create_client() -> Result<serenity::Client, Error>
{
    let cfg = Configuration::get().discord;

    let framework = poise::Framework::<Services, Error>::builder()
        .options(poise::FrameworkOptions {
            commands: vec![],
            prefix_options: poise::PrefixFrameworkOptions {
                prefix: Some(cfg.prefix),
                ..Default::default()
            },
            ..Default::default()
        })
        .setup(move |ctx, _, framework| {
            Box::pin(async move {
                poise::builtins::register_globally(ctx, &framework.options().commands).await?;
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
