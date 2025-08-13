# Configuring Authentik for Single Sign-On (SSO)

This guide will walk you through the process of setting up Authentik as an SSO provider for the Flask Address Book application.

## Step 1: Create an OAuth2/OpenID Provider in Authentik

First, you need to create a provider that will handle the authentication requests.

1.  **Navigate to Providers:** In your Authentik admin interface, go to **Applications** -> **Providers**.
2.  **Create a New Provider:** Click **Create** and select **OAuth2/OpenID Provider**.
3.  **Name the Provider:** Give it a descriptive name, for example, `Address Book Provider`.
4.  **Authorization Flow:** Select `default-provider-authorization-explicit-consent`.
5.  **Client Type:** Choose `Confidential`.
6.  **Redirect URIs/Origins:** This is the most important step. You need to tell Authentik where it's allowed to send users back to after they log in. Add the following URL to the list, making sure to replace `http://localhost:5000` with the actual URL of your Flask application:
    ```
    http://localhost:5000/authorize/authentik
    ```
7.  **Signing Key:** Select any of your available signing keys.
8.  **Save:** Click **Finish** to create the provider.

## Step 2: Create an Application in Authentik

Next, create the application that users will see and interact with.

1.  **Navigate to Applications:** Go to **Applications** -> **Applications**.
2.  **Create a New Application:** Click **Create**.
3.  **Name and Slug:** Give the application a name (e.g., `Address Book`) and a slug (e.g., `address-book`).
4.  **Provider:** In the **Provider** dropdown, select the `Address Book Provider` you just created.
5.  **Save:** Click **Finish**.

## Step 3: Get Your Credentials

Authentik will now have the credentials your Flask application needs to communicate with it.

1.  **View Provider:** Go back to **Applications** -> **Providers** and click on the `Address Book Provider` you created.
2.  **Find Credentials:** You will see the **Client ID** and **Client Secret**. Keep this page open, as you will need to copy these values.

## Step 4: Configure the Flask Application

Finally, update the `.env` file in your Flask application's root directory with the credentials from Authentik.

1.  **Open `.env` file:** Open the `.env` file in your text editor.
2.  **Fill in the Authentik variables:** Find the `AUTHENTIK` section and paste the values you got from Authentik. You also need to provide the base URL for your Authentik instance.

    ```dotenv
    # Authentik
    AUTHENTIK_CLIENT_ID="<PASTE YOUR CLIENT ID HERE>"
    AUTHENTIK_CLIENT_SECRET="<PASTE YOUR CLIENT SECRET HERE>"
    AUTHENTIK_SERVER_URL="[https://authentik.yourdomain.com/application/o/address-book/](https://authentik.yourdomain.com/application/o/address-book/)"
    ```
    **Important:** Make sure the `AUTHENTIK_SERVER_URL` ends with the slug of your application and a trailing slash.

3.  **Restart the Application:** Stop and restart your Flask application for the new environment variables to be loaded.

You should now see a "Sign In with Authentik" button on your login page, and it will redirect you to Authentik to handle the authentication.

