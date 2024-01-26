use std::fmt::Display;

use super::game::GameId;

use anyhow::{Error, Result};
use poise::serenity_prelude::model::id::UserId;
use serde::{Deserialize, Serialize};

/// A feedback entry for a Storyteller.
/// Each feedback entry needs an attached game, reporter and reportee.
/// An entry consists of:
/// - quantitative metrics
/// - text comments
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Feedback
{
    pub uuid: u64,
    pub game_id: GameId,
    pub storyteller: UserId,
    pub reporter: UserId,
    pub ratings: FeedbackRatings,
    pub comments: FeedbackComments,
    pub sharing: FeedbackVisibility
}

#[derive(Clone, Debug, Serialize, Deserialize, poise::Modal)]
#[name = "Open-Ended Comments"]
pub struct FeedbackComments
{
    #[name = "How could this Storyteller improve?"]
    #[placeholder = "Feel free to provide specific, actionable feedback on the storytelling this game."]
    #[paragraph]
    pub advice: Option<String>,

    #[name = "Do you have any other comments or concerns?"]
    #[placeholder = "Feel free to leave comments on things not already covered elsewhere in your feedback."]
    #[paragraph]
    pub other: Option<String>
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FeedbackRatings
{
    pub enjoyable: usize,
    pub organized: usize,
    pub daytime: usize,
    pub nighttime: usize
}

#[derive(Clone, Debug, Serialize, Deserialize, poise::Modal)]
#[name = "Quantitative Ratings"]
pub struct FeedbackRatingsModal
{
    #[name = "How enjoyable was the game?"]
    #[placeholder = "Enter a number from 1 to 5."]
    pub enjoyable: String,

    #[name = "How organized did the game feel?"]
    #[placeholder = "Enter a number from 1 to 5."]
    pub organized: String,

    #[name = "Were the day phases run well?"]
    #[placeholder = "Enter a number from 1 to 5."]
    pub daytime: String,

    #[name = "Were the night phases run well?"]
    #[placeholder = "Enter a number from 1 to 5."]
    pub nighttime: String
}

impl FeedbackRatingsModal
{
    /// Parses the response into the numeric model.
    pub fn to_ratings (& self) -> Result<FeedbackRatings, Error>
    {
        Ok(FeedbackRatings
        {
            enjoyable: self.enjoyable.parse::<usize>()?,
            organized: self.organized.parse::<usize>()?,
            daytime: self.daytime.parse::<usize>()?,
            nighttime: self.nighttime.parse::<usize>()?
        })
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, poise::ChoiceParameter)]
pub enum FeedbackVisibility
{
    #[name = "Share with my username attached"]
    WithUsername,

    #[name = "Share anonymously"]
    Anonymously,

    #[name = "Only share with the moderators"]
    Private
}

impl Default for FeedbackVisibility
{
    fn default() -> Self 
    {
        FeedbackVisibility::Anonymously    
    }
}

impl Display for FeedbackVisibility
{
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result 
    {
        write!(f, "{}", match self {
            FeedbackVisibility::WithUsername => "public",
            FeedbackVisibility::Anonymously => "anonymous",
            FeedbackVisibility::Private => "private"
        })
    }
}
