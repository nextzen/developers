'use strict';

const axios = require('axios');
const querystring = require('querystring');
const LRU = require("lru-cache"),
      lru = LRU(100);
const ONE_HOUR = 1 * 60 * 60 * 1000;

exports.handler = (event, context, callback) => {
    const request = event.Records[0].cf.request;
    console.log(lru.length + " keys in the lru");

    // Don't check for the preview.html page
    if (request.uri === '/preview.html') {
        return callback(null, request);
    }

    const params = querystring.parse(request.querystring);

    if (!params.api_key) {
        const response = {
            status: '400',
            statusDescription: 'Missing API Key',
            body: 'An API key is required.'
        };
        return callback(null, response);
    }

    const verify_params = {
        api_key: params.api_key,
    };

    if (request.headers['origin']) {
        verify_params.origin = request.headers['origin'][0].value;
    }

    const verify_querystring = querystring.stringify(verify_params);

    console.log("Verify params are " + JSON.stringify(verify_querystring));
    let cached_response = lru.get(verify_querystring);

    console.log("Cached response is " + JSON.stringify(cached_response));
    if (cached_response) {
        console.log("Using cached response.");
        var response;
        if (cached_response.result == 'success') {
            response = request;
        } else {
            response = {
                status: '400',
                statusDescription: 'Invalid API Key',
                body: cached_response.message
            };
        }
        return callback(null, response);
    }

    const verify_url = 'https://developers.nextzen.org/verify?' + verify_querystring;

    axios.get(verify_url, {timeout: 750})
        .then(function (response) {
            console.log(`Received verify response ${JSON.stringify(response.data)}`);

            lru.set(verify_querystring, response.data, ONE_HOUR);

            console.log(`Set key ${verify_querystring} to ${JSON.stringify(response.data)}`);

            return request;
        })
        .catch(function (error) {
            if (error.code === 'ECONNABORTED') {
                console.log('Timed out waiting for API key check');
                return request;
            } else if (error.response.status == 400) {
                console.log(`Received verify response ${JSON.stringify(error.response.data)}`);
                lru.set(verify_querystring, error.response.data, ONE_HOUR);
                return callback(null, {
                    status: '400',
                    statusDescription: 'Invalid API Key',
                    body: error.response.data.message
                });
            } else {
                console.log(error);
            }
        });
};
