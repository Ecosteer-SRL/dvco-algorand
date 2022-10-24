# dvco-algorand
Intermediation integration with Algorand

## Worker

The configuration entry for the worker component follows the yaml specification. The worker requires the following configuration for its integration with Algorand.


>   path:   '/home/ecosteer/dvco/algorand/worker/worker_algorand.py' 

>  	provider: 'workerAlgorand'

>  	configuration: 'atokf=/home/ecosteer/dop/externals/algorand/net1/Primary/algod.token; 
>>      atoken=ALGO_TOKEN;            
>>		anetf=/home/ecosteer/dop/externals/algorand/net1/Primary/algod.net;
>>		anetip=ALGO_IP; 
>>      anetprt=ALGO_PRT;
>>		ktokf=/home/ecosteer/dop/externals/algorand/net1/Primary/kmd.token;
>>		knetf=/home/ecosteer/dop/externals/algorand/net1/Primary/kmd.net;
>>		ktoken=KMD_TOKEN;
>>		knetip=KMD_IP;
>>		knetprt=KMD_PRT;
>>		scrf=/home/ecosteer/dvco/algorand/worker; 
>>		sttp=dop.account.teal.template;
>>		tapp=dop.stateful.teal;
>>		tcpp=basicClear.teal;
>>		userwlab=USER_WALL;
>> 		userpwd=UW_PWD;
>> 		ownmne=OWN_MNEMONIC;'

The required entries in the configuration string are:
- atokf - absolute path of the algod.token file 
- atoken - algod token (if this is defined then atokf will not be used)
- anetf - absolute path of the algod.net file; Contains information about IP address and the port where algo node can be reached
- anetip - algod tcp ip address (if this is defined then the anetf will not be used - anetprt required)
- anetprt - algod tcp ip port (if this is defined then the anetf will not be used - anetip required)
- ktokf - absolute path of the kmd.token file
- ktoken - kmd token (if this is defined then ktokf will not be used)
- knetf - absolute path of the kmd.net file, containing contact information of KMD
- knetip - kmd tcp ip address (if this is defined then the knetf will not be used - knetprt required); the IP address where the kmd can be reached
- knetprt - kmd tcp ip port (if this is defined then the knetf will not be used - knetip required)
- scrf - smart contract root folder: absolute path of the folder containing sttp, atpt and tcpp
- sttp - stateless teal template path: relative path of the stateless teal template
- tapp - teal approval program path: relative path of the teal approval program
- tcpp - teal clear program path: relative path of the teal clear program
- userwlab - user wallet (the wallet used by the worker to create accounts)
- userpwd - user wallet password
- ownmne - mnemonic of the owner account to be used to fund newly created accounts

## Proxy

Proxy component requires the following configuration file for Algorand provider. 

>> 		"provider": {
>> 		        "path": "/home/ecosteer/dop/provider/javascript/intermediation/algorand/cache_algo.js",
>> 			"conf": "store=/home/ecosteer/dop/stack/proxy/javascript/store/storeFileAlgo.json;nodeToken=NODE_EX_TOKEN;nodeTokenPath=NODE_TOKEN_PATH;nodePort=NODE_EX_PORT;nodePortPath=NODE_PORT_PATH;nodeServer=NODE_HOST;DOPalgorand=/home/ecosteer/dop/provider/javascript/intermediation/algorand/DOPalgorand.js"
>> 		    } 

store - a path to the storeFile.json file where the key-value pairs will be stored for persistence and retrieved upon the initialization of the provider to then be stored in key-value array.
nodeToken – Algorand token; used when Algorand node is external. If the node is internal, you must leave this blank.
nodeTokenPath – path to a file with Algorand token; used when Algorand node is internal. If the node is external, you must leave this blank.
nodePort - a port to which Algorand blockchain is listening; used when Algorand node is external. If the node is internal, you must leave this blank.
nodePortPath – path to a file with Algorand port; used when Algorand node is internal. If the node is external, you must leave this blank.
nodeServer - a host on which the Algorand blockchain is running.
DOPalgorand - a path to the DOPalgorand.js file, which establishes the main method to interact with the Smart Contract on the Algorand blockchain.
