import test from "node:test";
import assert from "node:assert/strict";
import {mediaBuildConfig,mediaServerMatches} from "../src/services/nativeCallConfig.js";
const env={mode:"media-staging",webOrigin:"https://staging.example.test",signalUrl:"wss://media-staging.example.test/signal",location:{origin:"https://staging.example.test"},secure:true};
test("only exact experimental origin can load media",()=>{
 const local=mediaBuildConfig(env);
 assert.deepEqual(local,{signalUrl:env.signalUrl});
 assert.equal(mediaBuildConfig({...env,mode:"production"}),null);
 assert.equal(mediaBuildConfig({...env,secure:false}),null);
 assert.equal(mediaBuildConfig({...env,location:{origin:"https://nkata.date"}}),null);
 assert.equal(mediaBuildConfig({...env,signalUrl:"wss://nkata.date/signal"}),null);
 assert.equal(mediaBuildConfig({...env,signalUrl:"ws://media-staging.example.test/signal"}),null);
 assert.equal(mediaServerMatches(local,{enabled:true,signal_url:env.signalUrl}),true);
 assert.equal(mediaServerMatches(local,{enabled:true,signal_url:"wss://other.example.test/signal"}),false);
 assert.equal(mediaServerMatches(local,{enabled:false,signal_url:env.signalUrl}),false);
});
