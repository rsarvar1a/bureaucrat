use poise::serenity_prelude::model::id::{ChannelId, GuildId};
use serde::{Deserialize, Serialize};

/// A primary key for a game of Clocktower. Each game 
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct GameId
{
    pub guild: GuildId,
    pub channel: ChannelId,
}

pub struct Game
{
    id: GameId,
}
