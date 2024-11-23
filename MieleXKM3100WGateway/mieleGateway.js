// How to use:
// 1. Set the WLAN of your Miele device with the Miele app.
// 2. Do NOT add the device to the Miele app after it is connected to your network!
// 3. Find out the IP address of your Miele device.
// 4. Run this Node.js app and browse to http://127.0.0.1:3000/init/<IP-ADDRESS>/ (replace <IP-ADDRESS> with the IP address of your Miele device).
// 5. If you get a 403 error, you need to sniff the groupKey and groupId from the Miele app.
// 6. If the init succeeded, you can now explore the data of your Miele device by browsing to http://127.0.0.1:3000/explore/<IP-ADDRESS>/.
// 7. When you have found the data you are interested in, you can extract it from other programs without the /explore option (http://127.0.0.1:3000/<IP-ADDRESS>/<PATH>). This will give you the raw JSON data.

const express = require('express');
const app = express();
const http = require('http').Server(app);
const request = require('superagent');
const crypto = require('crypto');
const dateFormat = require('dateformat');
const morgan = require('morgan');
const helmet = require('helmet');
const cors = require('cors');

// Middleware setup
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Debug flag
const debugLog = false;

// You don't need to change this if you use the init function.
// But it is recommended if you can't trust your local network.
const groupKey = Buffer.from(
  process.env.GROUP_KEY ||
    '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
  'hex'
);
const groupId = Buffer.from(
  process.env.GROUP_ID || '0000000000000000',
  'hex'
);

const acceptHeader = 'application/vnd.miele.v1+json';

// Utility functions
const getCurrentTimeInHttpFormat = () => {
  const d = new Date();
  d.setTime(d.getTime() + d.getTimezoneOffset() * 60 * 1000);
  return dateFormat(d, 'ddd, dd mmm yyyy HH:MM:ss') + ' GMT';
};

const isValidIP = (ip) => {
  return /^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(\.(?!$)|$){4}$/.test(ip);
};

const iterateToAllHrefs = (obj, host, resourcePath) => {
  for (const property in obj) {
    if (obj.hasOwnProperty(property)) {
      if (typeof obj[property] === 'object') {
        iterateToAllHrefs(obj[property], host, resourcePath);
      } else if (property === 'href') {
        obj[property] = `<a href="/explore/${host}${resourcePath}${obj[property]}">${obj[property]}</a>`;
      }
    }
  }
};

const decrypt = (payload, groupKey, signature) => {
  const key = groupKey.slice(0, groupKey.length / 2);
  const ivBuf = Buffer.from(signature, 'hex');
  const iv = ivBuf.slice(0, ivBuf.length / 2);

  const decipher = crypto.createDecipheriv('aes-256-cbc', key, iv);
  const data = Buffer.concat([
    decipher.update(Buffer.concat([payload, Buffer.from('00', 'hex')])),
    decipher.final(),
  ]);
  return data;
};

// Route handlers
app.get('/init/*', async (req, res) => {
  if (debugLog) console.log('GET:', req.url);

  let resourcePath = req.url.replace('/init', '');
  const hostMatch = resourcePath.match(/^\/([^/]+)/);
  const host = hostMatch ? hostMatch[1] : '';

  if (!host || !isValidIP(host)) {
    return res.status(400).json({ error: 'Invalid or missing IP address' });
  }

  resourcePath = resourcePath.replace(`/${host}`, '');

  try {
    const actDate = getCurrentTimeInHttpFormat();
    const response = await request
      .put(`http://${host}/Security/Commissioning/`)
      .set('Accept', acceptHeader)
      .set('Date', actDate)
      .set('User-Agent', 'Miele@mobile 2.3.3 Android')
      .set('Host', host)
      .set('Accept-Encoding', 'gzip')
      .timeout({
        response: 5000, // Wait 5 seconds for the server to start sending,
        deadline: 10000, // but allow 10 seconds for the file to finish loading.
      })
      .send({
        GroupID: groupId.toString('hex').toUpperCase(),
        GroupKey: groupKey.toString('hex').toUpperCase(),
      });

    res.json(response.body);
  } catch (err) {
    console.error(`Error during /init request to ${host}:`, err.message);
    const status = err.status || 500;
    const errorMessage = err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT'
      ? 'Appliance gateway is unavailable'
      : err.message || 'Initialization failed';
    res.status(status).json({ error: errorMessage });
  }
});

app.get('/*', async (req, res) => {
  if (req.url === '/favicon.ico') {
    return res.end();
  }
  if (debugLog) console.log('GET:', req.url);

  let explore = false;
  let resourcePath = req.url;

  if (resourcePath.startsWith('/explore')) {
    resourcePath = resourcePath.replace('/explore', '');
    explore = true;
  }

  const hostMatch = resourcePath.match(/^\/([^/]+)/);
  const host = hostMatch ? hostMatch[1] : '';

  if (!host || !isValidIP(host)) {
    return res.status(400).json({ error: 'Invalid or missing IP address' });
  }

  resourcePath = resourcePath.replace(`/${host}`, '');

  try {
    const actDate = getCurrentTimeInHttpFormat();
    const signatureStr = `GET\n${host}${resourcePath}\n\n${acceptHeader}\n${actDate}\n`;
    const signature = crypto
      .createHmac('sha256', groupKey)
      .update(Buffer.from(signatureStr, 'ascii'))
      .digest('hex')
      .toUpperCase();

    const response = await request
      .get(`http://${host}${resourcePath}`)
      .set('Accept', acceptHeader)
      .set('Date', actDate)
      .set('User-Agent', 'Miele@mobile 2.3.3 Android')
      .set('Host', host)
      .set(
        'Authorization',
        `MieleH256 ${groupId.toString('hex').toUpperCase()}:${signature}`
      )
      .set('Accept-Encoding', 'gzip')
      .buffer(true)
      .timeout({
        response: 5000, // Wait 5 seconds for the server to start sending,
        deadline: 10000, // but allow 10 seconds for the file to finish loading.
      })
      .parse((res, callback) => {
        res.rawBody = Buffer.alloc(0);
        res.on('data', (chunk) => {
          res.rawBody = Buffer.concat([res.rawBody, chunk]);
        });
        res.on('end', () => {
          callback(null, res);
        });
      });

    const responseSignature = response.header['x-signature'];
    const sigParts = responseSignature ? responseSignature.split(':') : [];
    const serverSignature = sigParts.length >= 2 ? sigParts[1] : '';

    const data = decrypt(response.rawBody, groupKey, serverSignature);
    const dataStr = data.toString('utf8');

    if (explore) {
      const jsonData = JSON.parse(dataStr);
      iterateToAllHrefs(jsonData, host, resourcePath);
      res.send(`
        <html>
          <head>
            <title>Explore Miele Device</title>
            <style>
              body { font-family: monospace; white-space: pre; }
              a { color: blue; text-decoration: none; }
              a:hover { text-decoration: underline; }
            </style>
          </head>
          <body>${JSON.stringify(jsonData, null, 4)}</body>
        </html>
      `);
    } else {
      res.json(JSON.parse(dataStr));
    }
  } catch (err) {
    console.error(`Error during request to ${host}${resourcePath}:`, err.message);
    const status = err.status || 500;
    const errorMessage = err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT'
      ? 'Appliance gateway is unavailable'
      : err.message || 'Request failed';
    res.status(status).json({ error: errorMessage });
  }
});

// Start the server
http.listen(3000, () => {
  console.log('Listening on http://127.0.0.1:3000');
});

// Graceful shutdown
process.on('SIGINT', () => {
  http.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

// Handle uncaught exceptions and rejections
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  // Decide whether to exit or not
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Decide whether to exit or not
});
