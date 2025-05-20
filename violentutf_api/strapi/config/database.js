module.exports = ({ env }) => {
  // Default configuration for local development
  let dbConfig = {
    client: env('DATABASE_CLIENT', 'postgres'),
    connection: {
      host: env('DATABASE_HOST', 'localhost'),
      port: env.int('DATABASE_PORT', 5432),
      database: env('DATABASE_NAME', 'strapi'),
      user: env('DATABASE_USERNAME', 'strapi'),
      password: env('DATABASE_PASSWORD', 'strapipassword'),
      ssl: false,
    },
    debug: env.bool('DATABASE_DEBUG', false),
    pool: {
      min: env.int('DATABASE_POOL_MIN', 2),
      max: env.int('DATABASE_POOL_MAX', 10),
    },
  };

  // Handle Cloud Foundry VCAP_SERVICES if available
  if (process.env.VCAP_SERVICES) {
    try {
      const vcapServices = JSON.parse(process.env.VCAP_SERVICES);
      
      console.log('Available VCAP_SERVICES keys:', Object.keys(vcapServices));
      
      // Look for postgres service with flexible naming
      let pgService = null;
      
      // Check potential service names - common postgres service names in CF
      const possibleServiceNames = ['strapiDB2025', 'aws-rds'];
      
      for (const serviceName of possibleServiceNames) {
        if (vcapServices[serviceName] && vcapServices[serviceName].length > 0) {
          pgService = vcapServices[serviceName][0];
          console.log(`Found PostgreSQL service under "${serviceName}" key`);
          break;
        }
      }
      
      // If we still don't have a service, check for user-provided service
      if (!pgService && vcapServices['user-provided'] && vcapServices['user-provided'].length > 0) {
        for (const service of vcapServices['user-provided']) {
          if (service.name.toLowerCase().includes('postgres') || 
              service.name.toLowerCase().includes('psql') || 
              service.name.toLowerCase().includes('db') || 
              service.name === 'strapiDB') {
            pgService = service;
            console.log(`Found potential PostgreSQL user-provided service: ${service.name}`);
            break;
          }
        }
      }
      
      if (pgService) {
        const credentials = pgService.credentials;
        
        console.log(`Found database credentials for service: ${pgService.name}`);
        
        // CRITICAL FIX FOR SELF-SIGNED CERTIFICATES
        // Use the node-postgres connection directly instead of using the URL
        // This allows us to properly set the SSL configuration
        
        if (credentials.uri || credentials.url) {
          console.log('Found connection URI, parsing for direct connection');
          try {
            // Parse the connection string
            const connectionStr = credentials.uri || credentials.url;
            
            // Extract components from URI (safely)
            let user, password, host, port, database;
            
            // Parse connection string - handle different formats
            if (connectionStr.startsWith('postgres://')) {
              const matches = connectionStr.match(/postgres:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)/);
              if (matches && matches.length >= 6) {
                [, user, password, host, port, database] = matches;
                // Remove query parameters from database if present
                database = database.split('?')[0];
              }
            }
            
            console.log(`Extracted connection details: host=${host}, port=${port}, database=${database}, user=${user}`);
            
            // Set up connection with explicit SSL settings to accept self-signed certs
            dbConfig = {
              client: 'postgres',
              connection: {
                host: host || credentials.host || credentials.hostname,
                port: parseInt(port || credentials.port),
                database: database || credentials.database || credentials.name || credentials.dbname,
                user: user || credentials.user || credentials.username,
                password: password || credentials.password,
                ssl: { 
                  rejectUnauthorized: false // CRITICAL: Accept self-signed certificates
                }
              },
              debug: env.bool('DATABASE_DEBUG', false),
              pool: {
                min: env.int('DATABASE_POOL_MIN', 2),
                max: env.int('DATABASE_POOL_MAX', 10),
              },
            };
            
          } catch (parseError) {
            console.error('Error parsing connection string:', parseError);
            
            // Fallback to using the connection string directly with special parameters
            console.log('Falling back to connection string with SSL params');
            
            let connStr = credentials.uri || credentials.url;
            // Add sslmode=require&ssl=true to the connection string
            connStr += (connStr.includes('?') ? '&' : '?') + 'sslmode=no-verify&ssl=true';
            
            dbConfig = {
              client: 'postgres',
              connection: connStr,
              debug: env.bool('DATABASE_DEBUG', false),
              pool: {
                min: env.int('DATABASE_POOL_MIN', 2), 
                max: env.int('DATABASE_POOL_MAX', 10),
              },
            };
          }
        } else {
          // Use individual credential fields with SSL settings
          dbConfig = {
            client: 'postgres',
            connection: {
              host: credentials.hostname || credentials.host,
              port: parseInt(credentials.port),
              database: credentials.name || credentials.database || credentials.dbname,
              user: credentials.username || credentials.user,
              password: credentials.password,
              ssl: { 
                rejectUnauthorized: false // CRITICAL: Accept self-signed certificates
              }
            },
            debug: env.bool('DATABASE_DEBUG', false),
            pool: {
              min: env.int('DATABASE_POOL_MIN', 2),
              max: env.int('DATABASE_POOL_MAX', 10),
            },
          };
        }
        
        console.log(`Configured database connection with SSL and self-signed certificate handling enabled`);
        
        // Additional environment setting to handle self-signed certificates globally
        // This is just added as an extra safety measure
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
        
      } else {
        console.log('No PostgreSQL service found in VCAP_SERVICES. Available services:', Object.keys(vcapServices));
      }
    } catch (error) {
      console.error('Error parsing VCAP_SERVICES:', error);
    }
  } else {
    console.log('No VCAP_SERVICES environment variable found, using default database configuration');
  }

  // Log the final database configuration (safely - without password)
  const safeConfig = { ...dbConfig };
  if (safeConfig.connection && typeof safeConfig.connection === 'object') {
    safeConfig.connection = { ...safeConfig.connection, password: '***' };
  }
  console.log('Final database configuration:', JSON.stringify(safeConfig, null, 2));

  return { connection: dbConfig };
};