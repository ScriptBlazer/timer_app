# Telegram Registration Approval Setup

This application includes a Telegram bot integration that sends you notifications when new users try to register. You can approve or deny registrations directly from Telegram.

## How It Works

1. **User Registration**: When someone tries to register, instead of creating an account immediately, their request is stored as "pending"
2. **Telegram Notification**: You receive a Telegram message with the user's details and two buttons: "Approve" and "Deny"
3. **Approval**: Click "Approve" to create the user account - they can then log in
4. **Denial**: Click "Deny" to reject the registration

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat and send: `/newbot`
3. Follow the prompts:
   - Give your bot a name (e.g., "Timer App Approvals")
   - Give it a username (e.g., "timer_app_approvals_bot")
4. BotFather will give you a **bot token** that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
5. Save this token - you'll need it for the `.env` file

### Step 2: Get Your Chat ID

1. Open Telegram and search for **@userinfobot**
2. Start a chat with it
3. It will immediately show your **Chat ID** (a number like `123456789`)
4. Save this ID - you'll need it for the `.env` file

### Step 3: Start a Chat with Your Bot

1. Search for your bot in Telegram (the username you created in Step 1)
2. Click "Start" or send `/start` to begin a conversation
3. This is important - the bot can only send you messages after you've started a chat with it

### Step 4: Configure Your Application

Add these lines to your `.env` file:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_step_1
TELEGRAM_ADMIN_CHAT_ID=your_chat_id_from_step_2
```

Replace the values with your actual bot token and chat ID.

### Step 5: Restart Your Application

If your application is running, restart it so it picks up the new environment variables:

```bash
# Stop the server (Ctrl+C if running)
# Then restart:
./start.sh
```

## Testing

1. Open your application's registration page (while logged out)
2. Try to register a new user
3. You should see a "Registration Pending Approval" page
4. Check your Telegram - you should receive a message with Approve/Deny buttons
5. Click "Approve" - the user account will be created
6. The user can now log in with their credentials

## Admin Panel

Pending registrations also appear in the Admin Panel (visible to workspace owners only). You can approve or deny them from there as well.

## Troubleshooting

### Not Receiving Telegram Messages?

1. **Check your bot token and chat ID** - Make sure they're correct in `.env`
2. **Start the bot** - You must have started a conversation with your bot first
3. **Restart the application** - Changes to `.env` require a restart
4. **Check console output** - If there's an error sending the message, it will print to the console

### Testing in Development

The Telegram notifications work the same in development and production. Just make sure your `.env` file has the correct credentials.

## Security Notes

- Your bot token is like a password - keep it secret
- Never commit your `.env` file to version control (it's already in `.gitignore`)
- The approval tokens are unique UUIDs, so the approval/deny links can't be guessed
- Pending registrations are automatically tied to unique tokens for security

## Disabling Telegram Notifications

If you want to disable Telegram notifications (for testing or development):

1. Remove or comment out the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID` from your `.env` file
2. Restart the application
3. Registration requests will still be stored as pending, but no Telegram messages will be sent
4. You can still approve/deny from the Admin Panel

## Production Deployment

When deploying to production:

1. Set the same environment variables on your production server
2. Make sure your production URL is accessible (the Telegram buttons use absolute URLs)
3. Test the registration flow in production to ensure notifications work

## Questions?

If you have any questions about the Telegram integration, check the main README or contact support.

