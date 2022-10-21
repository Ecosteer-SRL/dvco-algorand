
//  vers:   1.0
//  date:   16/Nov/2021
//  auth:   graz

'use strict'

const fs        = require('fs')
const algosdk   = require('algosdk');

class DOPalgorand
{
    constructor()
    {
        this._i_token   = '';       //  algo node token
        this._i_port    = -1;       //  algo node port

        //  in order to "communicate" with an algorand node it is necessary to know
        //  1)  its token
        //  2)  the port it's listening to
        //  the token and the port are found in two (local in respect to the node) files:
        //  $ALGORAND_DATA/algod.token (contains the token)
        //  $ALGORAND_DATA/algod.net
        this._i_token_file   = process.env.ALGORAND_DATA + '/algod.token';
        this._i_net_file     = process.env.ALGORAND_DATA + '/algod.net';
    }

    algodToken()
    {
        if (this._i_token != '') { return { err: 0, val: this._i_token}; }

        //  this._i_token not assigned yet
        try {
            let data = fs.readFileSync(this._i_token_file,{encoding: 'utf8',flag: 'r'});
            this._i_token = data;
            return { err: 0, val: data};
        }
        catch(err){
            return {err: 1, val: ''};
        }            
    }

    algodPort()
    {
        if (this._i_port != -1) { return { err: 0, val: this._i_port}; }

        //  this._i_port not assigned yet
        try {
            let data = fs.readFileSync(this._i_net_file,{encoding: 'utf8',flag: 'r'});
            //console.log(data)
            this._i_port = parseInt(data.split(':')[1],10);
            return {err: 0, val: this._i_port};
        }
        catch(err){
            return {err: 1, val: ''};
        }            
    }

    logToBuffer(logObj)
    {
        //  example of an encoded log (log object)
        /*
            { 
                '0': 116,
                '1': 104,
                '2': 105,
                '3': 115,
                '4': 95,
                '5': 105,
                '6': 115,
                '7': 95,
                '8': 97,
                '9': 95,
                '10': 108,
                '11': 111,
                '12': 103 
            }        
        */        
        if (typeof(logObj) != 'object') return { err: 1, val: null};
        let arr = [];
        
        //for (var prop in logObj) { logstring = logstring + String.fromCharCode(logObj[prop]); }
        for (var prop in logObj) { arr.push(logObj[prop]); }
        let buffer = Buffer.from(arr);
        return {err: 0, val: buffer};
    }

    async innerWaitForConfirmation 
    (
        algodClient     //  instamce of algosdk.Algodv2
    ,   txId            //  transaction ID
    ,   timeout
    ) 
    {
        if (algodClient == null || txId == null || timeout < 0) {
            throw new Error("Bad arguments");
        }
    
        const status = (await algodClient.status().do());
        if (status === undefined) {
            throw new Error("Unable to get node status");
        }
    

        //  NODE STATUS EXAMPLE
        //  {
        //    "catchpoint":"",
        //    "catchpoint-acquired-blocks":0,
        //    "catchpoint-processed-accounts":0,
        //    "catchpoint-total-accounts":0,
        //    "catchpoint-total-blocks":0,
        //    "catchpoint-verified-accounts":0,
        //    "catchup-time":0,
        //    "last-catchpoint":"20000#AVBR52FIJH7VXSAIVSMNU7ZVMV4VSJ2DADOT2XLFVFHEZYD3UDXA",
        //    "last-round":24180,
        //    "last-version":"https://github.com/algorandfoundation/specs/tree/bc36005dbd776e6d1eaf0c560619bb183215645c",
        //    "next-version":"https://github.com/algorandfoundation/specs/tree/bc36005dbd776e6d1eaf0c560619bb183215645c",
        //    "next-version-round":24181,
        //    "next-version-supported":true,
        //    "stopped-at-unsupported-round":false,
        //    "time-since-last-round":2362957778
        //  }

        const startround = status["last-round"] + 1;
        let currentround = startround;
    
        while (currentround < (startround + timeout)) {
            const pendingInfo = await algodClient.pendingTransactionInformation(txId).do();
            if (pendingInfo !== undefined) {
                if (pendingInfo["confirmed-round"] !== null && pendingInfo["confirmed-round"] > 0) {
                    //  the transaction property "confirmed-round" exists AND the property "confirmed-round" 
                    //  is greater than zero, so
                    //  => Got the completed Transaction, return the completed transaction
                    return pendingInfo;
                } else {
                    if (pendingInfo["pool-error"] != null && pendingInfo["pool-error"].length > 0) {
                        //  the property "pool-error" exists and the property "pool-error" has a lenght greater than zero
                        //  If there was a pool error, then the transaction has been rejected!
                        throw new Error("Transaction " + txId + " rejected - pool error: " + pendingInfo["pool-error"]);
                    }
                }
            }
            //  Waits for a specific round to occur then returns the StatusResponse for that round
            await algodClient.statusAfterBlock(currentround).do();
            //  Increment the current round
            currentround++;
        }
    
        throw new Error("Transaction " + txId + " not confirmed after " + timeout + " rounds!");
    };
    
    
    async waitForConfirmation
    (
        client        //  instamce of algosdk.Algodv2
    ,   txnId         //  transaction ID
    ) 
    {
        const roundTimeout = 2; //  maximum number of rounds before "timeout"
        //const completedTx = await utils.waitForConfirmation(
        const completedTx = await this.innerWaitForConfirmation(client,txnId,roundTimeout);

        return {err: 0, val: completedTx};
    }  
    
    
    async dopSmartContract
    (
        client
    ,   smart_contract_index
    ,   sender_mnemonic
    ,   scarguments                 //  {args: arrayofstringargs, addrs: arrayofaddresses}
    )
    {
        //  setting app-args
        let appArgs = [];
        if (typeof(scarguments.args) != 'undefined')
        {
          if (scarguments.args.length > 0)
          {
            scarguments.args.reverse();
            while (scarguments.args.length > 0)
            {
              let arg = scarguments.args.pop().toString();
              appArgs.push(new Uint8Array(Buffer.from(arg)));
            }
          }
        }
    
        //  TODO:
        //  need to find the way to pass addresses, too (arguments.addrs array)
    
        try 
        {    
          let accountSecretKey = algosdk.mnemonicToSecretKey(sender_mnemonic);
          let params = await client.getTransactionParams().do();
          params.fee = 1000;
          params.flatFee = true;
      
          // create unsigned transaction
          let callTxn = algosdk.makeApplicationNoOpTxn(
              accountSecretKey.addr, 
              params, 
              smart_contract_index, 
              appArgs
              );
      
        
      
          //  sign the transaction
          //  the transaction has to be signed with the secret key of the issuing account
          //  (the account that initiates the transaction)
          const signedCallTxn = callTxn.signTxn(accountSecretKey.sk);
      
          let txId = callTxn.txID().toString();
      
          //  console.log("Signed transaction with txID: %s", txId);
          //  TxId example: "VE2SDKL2XM5ELPMW2PXUQ36KMC5JJQ4M5DIH5RKJXBYVKPDHRYOQ"
      
          //===============================================================
          //  Submit the transaction (send transaction)
          //===============================================================
          let callTxnId;
          try {
            let res = await client.sendRawTransaction(signedCallTxn).do();
            callTxnId = res.txId;
          }
          catch (err)
          {
            return {err: 5000, val: err}
          }
      
      
          let confirmedTxn;
          try {
            //let ret = await utils.waitForConfirmation(client, callTxnId);
            let ret = await this.waitForConfirmation(client, callTxnId);
            if (ret.err == 0) 
            {
              confirmedTxn = ret.val;
            }
            else
            {
              //  ret.err != 0
              return ret; //  ret is {err:, val:}
            }
          }
          catch(err)
          {
            console.log(JSON.stringify(err));
            //process.exit();
            return {err: 5001, val: err}
          }
      
      
          //  logArray is the array that contains all the log (strings) produced by the smart contract
          //  the logs are the main way to pass results from the smart contract
          let logArray = [];
      
          if (typeof(confirmedTxn.logs) != 'undefined')
          {
            //  please verify the following
            for (let i=0; i<confirmedTxn.logs.length; i++) 
            {
                let res = this.logToBuffer(confirmedTxn.logs[i]);  //  {err,val]}
                if (res.err == 0)
                {
                  //  NOTE:
                  //  see man.txt re PROTOCOL
                  //  the log[0] is used for the integration (result value) with the smart contract
                  //  in practice log[0] will be used by the proxy provider in order to determine
                  //  if the key can be released/propagated to the requesting account
                  let logStr = res.val.toString('utf-8');
                  //  console.log('LOG(' + i.toString() + ')[' + logStr + ']');
                  logArray.push(logStr);
                }
            }
          }
      
          //====================================================================
          //  SOME USEFUL TRANSACTION INFORMATION
          //  console.log("Transaction " + txId + " confirmed in round " + confirmedTxn["confirmed-round"]);
      
          //  let mytxinfo = JSON.stringify(confirmedTxn.txn.txn, undefined, 2);
          //  console.log("Transaction information: %o", mytxinfo);
          //  '{\n  "apaa": [\n    {\n      "0": 103,\n      "1": 101,\n      "2": 116,\n      "3": 107,\n      "4": 101,\n      "5": 121\n    }\n  ],\n  "apid": 189,\n  "fee": 1000,\n  "fv": 31093,\n  "gen": "private-v1",\n  "gh": {\n    "0": 243,\n    "1": 153,\n    "2": 83,\n    "3": 58,\n    "4": 99,\n    "5": 62,\n    "6": 237,\n    "7": 186,\n    "8": 15,\n    "9": 175,\n    "10": 34,\n    "11": 131,\n    "12": 210,\n    "13": 16,\n    "14": 136,\n    "15": 88,\n    "16": 201,\n    "17": 28,\n    "18": 160,\n    "19": 160,\n    "20": 25,\n    "21": 101,\n    "22": 161,\n    "23": 89,\n    "24": 248,\n    "25": 104,\n    "26": 189,\n    "27": 97,\n    "28": 40,\n    "29": 173,\n    "30": 171,\n    "31": 72\n  },\n  "lv": 32093,\n  "snd": {\n    "0": 177,\n    "1": 88,\n    "2": 224,\n    "3": 100,\n    "4": 190,\n    "5": 153,\n    "6": 148,\n    "7": 202,\n    "8": 101,\n    "9": 195,\n    "10": 176,\n    "11": 155,\n    "12": 99,\n    "13": 198,\n    "14": 206,\n    "15": 170,\n    "16": 159,\n    "17": 125,\n    "18": 31,\n    "19": 128,\n    "20": 147,\n    "21": 44,\n    "22": 17,\n    "23": 77,\n    "24": 210,\n    "25": 24,\n    "26": 164,\n    "27": 255,\n    "28": 81,\n    "29": 138,\n    "30": 128,\n    "31": 63\n  },\n  "type": "appl"\n}'
          //====================================================================
      
      
          // display results
          let transactionResponse = await client.pendingTransactionInformation(callTxnId).do();
          //  console.log("Called app-id:",transactionResponse['txn']['txn']['apid'])
          //  Called app-id: 189
          
          //  SHOW CHANGES TO GLOBAL STATE and LOCAL STATE
          //  if (transactionResponse['global-state-delta'] !== undefined ) {
          //      console.log("Global State updated:",transactionResponse['global-state-delta']);
          //  }
      
          //  if (transactionResponse['local-state-delta'] !== undefined ) {
          //    console.log("Local State updated:",transactionResponse['local-state-delta']);
          //    Local State updated: [ { address: 'WFMOAZF6TGKMUZODWCNWHRWOVKPX2H4ASMWBCTOSDCSP6UMKQA7ZXUIURY',
          //  }
      
          return {err: 0, val: logArray};
        }
      
        catch(err) 
        {
          console.log("err",err);
          return {err: 5002, val: err}
        }
    }
    

};

module.exports = {
    DOPalgorand: DOPalgorand
};

