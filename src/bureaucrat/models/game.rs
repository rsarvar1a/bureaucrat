use poise::serenity_prelude::model::id::{ChannelId, GuildId};
use serde::{Deserialize, Serialize};

/*
 Each game is tied to a unique channel, and only one game can run in a given channel.
*/
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct GameId
{
    guild: GuildId,
    channel: ChannelId,
}

pub struct Game
{
    id: GameId,
}
