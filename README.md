# genshin account creator
A batch genshin account creator using selenium

All captchas must be solved by the user, there is a 60 second timeout if you take too long.

# usage
Run `python main.py` and wait for the accounts to be generated.
Every time a captcha pops out solve it.

# how it works
1. Create a [temp-mail](https://temp-mail.org/) address
2. Register through the [official website](https://account.mihoyo.com/#/register/email)
3. Wait for the confirmation code to arrive at your address
4. Verify your account
5. Login on [hoylabs](https://www.hoyolab.com/genshin/)
6. Create a new hoyolabs account using the email as the username
7. Fetch cookies by going to mihoyo's api subdomain.
8. Store the email, password, username and cookies.
9. Logout
