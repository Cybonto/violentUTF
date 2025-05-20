module.exports = ({ env }) => ({
    auth: {
      secret: env('ADMIN_JWT_SECRET', 'your_admin_jwt_secret'),
    },
    apiToken: {
      salt: env('API_TOKEN_SALT'),
    },
    transfer: { 
      token: { 
        salt: env('TRANSFER_TOKEN_SALT', 'anotherRandomLongString'),
      }
    }
  });