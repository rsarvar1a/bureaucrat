
use super::prelude::*;
use anyhow::{Error, Result};

/// Creates a new barebones embed.
pub async fn new_embed (ctx: & Context<'_>, title: & str) -> Result<serenity::CreateEmbed, Error>
{
    let bot = ctx.framework().bot_id.to_user(& ctx).await?;

    let mut author = serenity::CreateEmbedAuthor::new(title);
    let mut footer = serenity::CreateEmbedFooter::new(bot.name.clone());

    if let Some(url) = bot.avatar_url()
    {
        author = author.icon_url(url.clone());
        footer = footer.icon_url(url);
    }

    let embed = serenity::CreateEmbed::new()
        .author(author)
        .footer(footer);

    Ok(embed)
}
