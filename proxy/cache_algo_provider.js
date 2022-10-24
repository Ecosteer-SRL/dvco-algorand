//  version     3.0
//  date:       24/10/2022
//  author:     Gabriele Sankalaite

"use strict";

const providerVersion = "3.0";

// Required packages
const qs = require("qs");
const fs = require("fs");
const algosdk = require("algosdk");
const crypto = require("crypto");
const crc16 = require("js-crc").crc16;

// Main class to interact with local Algorand node
const DOPalgorand = require("./DOPalgorand.js");
const utils = new DOPalgorand.DOPalgorand();

// DOP package provider
class providerDopPackage {
  init(confString) {
    if (confString) {
      try {
        this.settings = qs.parse(confString, { delimiter: ";" });
        const perProv = this.settings["store"];

        const nodeTokenPath = this.settings["nodeTokenPath"];
        const nodePortPath = this.settings["nodePortPath"];
        const nodeServer = this.settings["nodeServer"];
        const nodeToken = this.settings["nodeToken"];
        const nodePort = this.settings["nodePort"];

        if (nodeToken && nodeToken != NaN) {
          if (nodePort && nodePort != NaN) {
            try {
              //  Instantiation of the client towards the Algorand node
              const client = new algosdk.Algodv2(
                nodeToken,
                nodeServer,
                nodePort
              );

              this.algod = client;
              return this.initStoreFile(perProv);
            } catch (error) {
              return 606;
            }
          } else {
            return 605;
          }
        } else if (
          nodeTokenPath &&
          nodeTokenPath != NaN &&
          fs.existsSync(nodeTokenPath)
        ) {
          if (
            nodePortPath &&
            nodePortPath != NaN &&
            fs.existsSync(nodePortPath)
          ) {
            let nodeToken = fs.readFileSync(nodeTokenPath, {
              encoding: "utf8",
              flag: "r",
            });

            let nodePort = fs.readFileSync(nodePortPath, {
              encoding: "utf8",
              flag: "r",
            });

            let nodePortFinal = parseInt(nodePort.split(":")[1], 10);

            try {
              //  Instantiation of the client towards the Algorand node
              const client = new algosdk.Algodv2(
                nodeToken,
                nodeServer,
                nodePortFinal
              );

              this.algod = client;
              return this.initStoreFile(perProv);
            } catch (error) {
              return 604;
            }
          } else {
            return 603;
          }
        } else {
          return 602;
        }
      } catch (error) {
        return 601;
      }
    } else {
      return 600;
    }
  }

  initStoreFile(storeFilePath) {
    // Instantiate keystore array
    this.cache = new Object();

    let content = "[]";

    // Create new file if file doesn't exist
    if (!fs.existsSync(storeFilePath)) {
      try {
        fs.writeFileSync(storeFilePath, content);
        return 0;
      } catch (error) {
        return 611;
      }
    }

    // Parse file if file exists

    try {
      const perCache = JSON.parse(fs.readFileSync(storeFilePath));
      if (Object.keys(perCache).length === 0) {
        return 0;
      } else {
        // Add existing key-value pairs to the keystore array
        for (const [key, value] of Object.entries(perCache)) {
          this.cache[key] = value;
        }
        return 0;
      }
    } catch (error) {
      return 612;
    }
  }

  async open() {
    const smCStatus = await this.algodTest();

    if (smCStatus === 1) {
      return 623;
    } else if (smCStatus.hasOwnProperty("last-round")) {
      const lastRound = smCStatus["last-round"];
      if (lastRound > 0) {
        return 0;
      } else {
        return 624;
      }
    } else {
      return 623;
    }
  }

  // Key integrity function
keyHashIntegrity(key) {
    const keyHash = crypto.createHash("sha256").update(key).digest("hex");
    const crc16keyHash = crc16(keyHash);
    return crc16keyHash;
}

  async pubKeySet(smContractIndex, key, kid, sec, creatorMnemonicBase64) {
    try {
      let smCInx = parseInt(smContractIndex);

      let buffer = Buffer.from(creatorMnemonicBase64, "base64");
      let creatorMnemonic = buffer.toString("ascii");
    
      const keyToSet = this.keyHashIntegrity(key.toString());

      let argsObj = {
        args: ["setkey", keyToSet, kid.toString()],
        addrs: [],
      };

      let result = await utils.dopSmartContract(
        this.algod,
        smCInx,
        creatorMnemonic,
        argsObj
      );

      let reply = result;

      try {
        let errValue = parseInt(reply.val[0].split("=")[1].split(";")[0]);
        if (errValue == 0) {
          try {
            const timestamp = Math.floor(new Date().getTime() / 1000);
            // Check if keystore array already has a key associated with a specific pid
            if (this.cache.hasOwnProperty(smContractIndex)) {
              // Check the number of keys already associated with a specific pid
              let keyStore = this.cache[smContractIndex];
              let keyStoreLength = keyStore.length;
              if (keyStoreLength < 2) {
                this.cache[smContractIndex].push({ key: key, kid: kid, timestamp: timestamp });
                return { error: 0, result: 0 };
              } else if (keyStoreLength === 2) {
                this.cache[smContractIndex].push({ key: key, kid: kid, timestamp: timestamp });
                this.cache[smContractIndex].shift();
                return { error: 0, result: 0 };
              } else if (keyStoreLength > 2) {
                while (keyStoreLength > 2) {
                  this.cache[smContractIndex].shift();
                  keyStoreLength = this.cache[smContractIndex].length;
                }
                this.cache[smContractIndex].push({ key: key, kid: kid, timestamp: timestamp });
                this.cache[smContractIndex].shift();
                return { error: 0, result: 0 };
              }
            } else {
              this.cache[smContractIndex] = [{ key: key, kid: kid, timestamp: timestamp }];
              return { error: 0, result: 0 };
            }
          } catch (error) {
            return { error: 631, result: false };
          }
        } else if (errValue == 255) {
          return { error: 643, result: false };
        }
      } catch (error) {
        return { error: 642, result: false };
      }
    } catch (error) {
      return { error: 641, result: false };
    }
  }

  async pubKeyGet(smContractIndex, kid, sec, creatorMnemonicBase64) {
    try {
      if (kid == 0 || kid === '0') {
        if (this.cache.hasOwnProperty(smContractIndex)) {
          let keys = this.cache[smContractIndex];
          let value = { key: keys[0].key, kid: keys[0].kid }
          return { error: 0, result: value };
        } else {
          return { error: 666, result: false };
        }
      } else {
        let smCInx = parseInt(smContractIndex);

        let buffer = Buffer.from(creatorMnemonicBase64, "base64");
        let creatorMnemonic = buffer.toString("ascii");

        let argsobj = {
          args: ["getkey", kid.toString()],
          addrs: [],
        };

        let result = await utils.dopSmartContract(
          this.algod,
          smCInx,
          creatorMnemonic,
          argsobj
        );

        let reply = result;

        try {
          if (reply.err == 5000) {
            // TransactionPool.Remember: transaction already in ledger
            return { error: 660, result: false };
          }
          let errValue = parseInt(reply.val[0].split("=")[1].split(";")[0]);
          if (errValue == 0) {
            if (this.cache.hasOwnProperty(smContractIndex)) {
              let keys = this.cache[smContractIndex];
              if (keys[0].kid === kid) {
                let value = { key: keys[0].key, kid: keys[0].kid }
                return { error: 0, result: value };
              } else if (keys[1].kid === kid) {
                let value = { key: keys[1].key, kid: keys[1].kid }
                return { error: 0, result: value };
              } else {
                return { error: 656, result: false };
              }
            } else {
              return { error: 655, result: false };
            }
          } else if (errValue == 10) {
            // Kid does not match
            return { error: 654, result: false };
          } else if (errValue == 255) {
            // Sender has requested an unsupported operation
            return { error: 653, result: false };
          }
        } catch (error) {
          return { error: 652, result: false };
        }
      }
    } catch (error) {
      return { error: 651, result: false };
    }
  }

  async subKeyGet(smContractIndex, kid, subscriberMnemonicBase64, sub) {
    try {
      let smCInx = parseInt(smContractIndex);

      let buffer = Buffer.from(subscriberMnemonicBase64, "base64");
      let subscriberMnemonic = buffer.toString("ascii");

      let argsobj = {
        args: ["getkey", kid.toString()],
        addrs: [],
      };

      let result = await utils.dopSmartContract(
        this.algod,
        smCInx,
        subscriberMnemonic,
        argsobj
      );

      let reply = result;

      try {
        if (reply.err == 5000) {
          // TransactionPool.Remember: transaction already in ledger
          return { error: 670, result: false };
        }

        let errValue = parseInt(reply.val[0].split("=")[1].split(";")[0]);

        if (errValue == 0) {
          if (this.cache.hasOwnProperty(smContractIndex)) {
            let keys = this.cache[smContractIndex];
            if (keys[0].kid === kid) {
              let value = { key: keys[0].key, kid: keys[0].kid }
              return { error: 0, result: value };
            } else if (keys[1].kid === kid) {
              let value = { key: keys[1].key, kid: keys[1].kid }
              return { error: 0, result: value };
            } else {
              return { error: 671, result: false };
            }
          } else {
            return { error: 665, result: false };
          }
        } else if (errValue == 1) {
          // The requested account is NOT SUBSCRIBED
          return { error: 669, result: false };
        } else if (errValue == 2) {
          // The requested account is NOT GRANTED
          return { error: 668, result: false };
        } else if (errValue == 3) {
          // The requested kid does not match the available kid
          return { error: 667, result: false };
        } else if (errValue == 4) {
          // The requested account has no credit
          return { error: 666, result: false };
        } else if (errValue == 255) {
          // Sender has requested an unsupported operation
          return { error: 663, result: false };
        }
      } catch (error) {
        return { error: 662, result: false };
      }
    } catch (error) {
      return { error: 661, result: false };
    }
  }

  async algodTest() {
    try {
      const smCStatus = await this.algod.status().do();
      if (smCStatus.hasOwnProperty("last-round")) {
        return smCStatus;
      } else {
        return 1;
      }
    } catch (error) {
      return 1;
    }
  }

  async test() {
    const providerName = __filename.slice(__dirname.length + 1, -3);
    const cacheLength = Object.keys(this.cache).length;

    if (cacheLength >= 0) {
      const smCStatus = await this.algodTest();

      if (smCStatus.hasOwnProperty("last-round")) {
        const lastRound = smCStatus["last-round"];
        if (lastRound > 0) {
          let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=0;pach=0;pblk=${lastRound};`;
          return { error: 0, result: testResult };
        } else {
          let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=0;pach=1;`;
          return { error: 695, result: testResult };
        }
      } else {
        let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=0;pach=1;`;
        return { error: 695, result: testResult };
      }
    } else {
      const smCStatus = await this.algodTest();

      if (smCStatus.hasOwnProperty("last-round")) {
        const lastRound = smCStatus["last-round"];
        if (lastRound > 0) {
          let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=1;pach=0;pblk=${lastRound};`;
          return { error: 697, result: testResult };
        } else {
          let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=1;pach=1;`;
          return { error: 698, result: testResult };
        }
      } else {
        let testResult = `psrv=${providerName};pver=${providerVersion};ptsk=persistanceOfKeysInMemoryAndAlgorandKeyValidation;pcch=1;pach=1;`;
        return { error: 698, result: testResult };
      }
    }
  }

  close() {
    try {
      const jsonCache = JSON.stringify(this.cache);
      const storePath = this.settings["store"];
      fs.writeFileSync(storePath, jsonCache);

      return 0;
    } catch (error) {
      return 613;
    }
  }
}

module.exports = providerDopPackage
;
