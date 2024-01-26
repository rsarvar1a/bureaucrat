
use super::{prelude::*, utils};
use crate::bureaucrat::models::{feedback::*, game::GameId};

/// Rate and/or comment on your Storyteller
#[command(
    prefix_command, slash_command,
    category = "Feedback"
)]
pub async fn submit(
    ctx: Context<'_>,
    #[description = "Who was your Storyteller?"]
    st: serenity::User,
    #[description = "Share your feedback with your Storyteller?"]
    mode: FeedbackVisibility
) -> Result
{
    let mut comments: Option<FeedbackComments> = None;
    let mut ratings: Option<FeedbackRatingsModal> = None;

    // This command doesn't work in DM channels.

    let guild = ctx.guild_id();
    
    if guild.is_none()
    {
        ctx.say("This command must be run in a server!").await?;
        return Ok(());
    }

    // Create the menu.

    let guild = guild.unwrap();
    let channel = ctx.guild_channel().await.unwrap();
    let game_id = GameId { guild, channel: channel.id };

    let feedback_view = feedback_embed(& ctx, & st, & mode, & comments, & ratings).await?;
    let buttons_row = create_feedback_buttons(& ctx, & comments, & ratings);

    let reply = poise::CreateReply::default()
        .components(vec![buttons_row]).embed(feedback_view).ephemeral(true).reply(true);

    ctx.send(reply.clone()).await?;

    // Collect responses to build the feedback entry.

    let uuid = ctx.id();

    while let Some(mci) = serenity::ComponentInteractionCollector::new(ctx.serenity_context())
        .timeout(std::time::Duration::from_secs(60 * 10))
        .filter(move |mci| mci.data.custom_id.starts_with(uuid.to_string().as_str()))
        .await
    {
        if mci.data.custom_id.ends_with("comments")
        {
            comments = poise::execute_modal_on_component_interaction::<FeedbackComments>(ctx, mci.clone(), comments.clone(), None).await?;
            update_feedback_view(& ctx, & mci, & st, & mode, & comments, & ratings).await?;
        }
        else if mci.data.custom_id.ends_with("ratings")
        {
            ratings = poise::execute_modal_on_component_interaction::<FeedbackRatingsModal>(ctx, mci.clone(), ratings.clone(), None).await?;
            update_feedback_view(& ctx, & mci, & st, & mode, & comments, & ratings).await?;
        }
        else if mci.data.custom_id.ends_with("submit")
        {
            let comments = comments.clone();
            let ratings = ratings.clone();

            if comments.is_none() || ratings.is_none()
            {
                continue;
            }
            let comments = comments.unwrap();

            if let Ok(ratings) = ratings.unwrap().to_ratings()
            {
                let feedback_entry = Feedback { uuid, game_id, storyteller: st.id, reporter: ctx.author().id, ratings, comments, sharing: mode };
                send_confirmation(& ctx, & mci, & st, & feedback_entry).await?;
                break;
            }
            else
            {
                let err_reply = poise::CreateReply::default().content("Ratings must be numbers!").ephemeral(true).reply(true);
                ctx.send(err_reply).await?;
            }
        }
        else
        {
            return Err(anyhow::anyhow!(format!("unrecognized interaction {}", mci.data.custom_id)));
        }
    }

    Ok(())
}

/// Creates an embed that shows the state of the feedback entry.
async fn feedback_embed(
    ctx: & Context<'_>, 
    st: & serenity::User, 
    mode: & FeedbackVisibility, 
    comments: & Option<FeedbackComments>, 
    ratings: & Option<FeedbackRatingsModal>
) -> anyhow::Result<serenity::CreateEmbed, Error>
{
    let full = ":white_check_mark:";
    let empty = ":x:";

    let embed = utils::new_embed(ctx, format!("Storyteller feedback for {}", st.name).as_str()).await?
        .description(format!("Your feedback is {}.\nClick the buttons below to fill out the feedback form.", mode))
        .field("Ratings", if ratings.is_some() { full } else { empty }, true)
        .field("Comments", if comments.is_some() { full } else { empty }, true);

    Ok(embed)
}

async fn update_feedback_view(
    ctx: & Context<'_>,
    mci: & serenity::ComponentInteraction,
    st: & serenity::User,
    mode: & FeedbackVisibility,
    comments: & Option<FeedbackComments>,
    ratings: & Option<FeedbackRatingsModal>,
) -> Result
{
    let view = feedback_embed(ctx, st, mode, comments, ratings).await?;
    let buttons = create_feedback_buttons(ctx, comments, ratings);

    mci.edit_response(
        ctx.serenity_context(), 
        serenity::EditInteractionResponse::new()
            .components(vec![buttons]).embed(view)
    ).await?;

    Ok(())
}

fn create_feedback_buttons(
    ctx: & Context<'_>, 
    comments: & Option<FeedbackComments>, 
    ratings: & Option<FeedbackRatingsModal>
) -> serenity::CreateActionRow
{
    let uuid = ctx.id();

    let full = serenity::ButtonStyle::Secondary;
    let empty = serenity::ButtonStyle::Primary;
    let active = serenity::ButtonStyle::Success;
    let can_submit = comments.is_some() && ratings.is_some();

    serenity::CreateActionRow::Buttons(
        vec![
            serenity::CreateButton::new(format!("{uuid}_ratings"))
                .style(if ratings.is_some() { full } else { empty })
                .label("Create ratings"),
            serenity::CreateButton::new(format!("{uuid}_comments"))
                .style(if comments.is_some() { full } else { empty })
                .label("Leave comments"),
            serenity::CreateButton::new(format!("{uuid}_submit"))
                .style(active)
                .label("Submit feedback")
                .disabled(! can_submit)
        ]
    )
}

/// Notifies the user.
async fn send_confirmation(
    ctx: & Context<'_>, 
    mci: & serenity::ComponentInteraction, 
    st: & serenity::User,
    entry: & Feedback
) -> Result
{
    mci.create_response(
        ctx.serenity_context(), 
        serenity::CreateInteractionResponse::UpdateMessage(
            serenity::CreateInteractionResponseMessage::new()
                .components(vec![]).ephemeral(true).embed(
                    utils::new_embed(&ctx, format!("Storyteller feedback for {}", st.name).as_str())
                        .await?.description("Feedback submitted; thank you!")
                )
        )
    ).await?;

    // Entry finalized and saved.

    let private_embed = utils::new_embed(& ctx, format!("Submitted feedback for {}", st.name).as_str())
        .await?
        .description(format!("```rust\n{:#?}\n```", entry));

    ctx.author().dm(& ctx, serenity::CreateMessage::new().embed(private_embed)).await?;
    Ok(())
}
