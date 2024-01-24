use super::game::GameId;

use poise::serenity_prelude::model::id::UserId;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct Feedback
{
    pub game_id: GameId,
    pub storyteller: UserId,
    pub reporter: UserId,
}
