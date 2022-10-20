 
#   ver:    0.5
#   date:   15/02/2022

import os
import base64
from typing import Tuple, Type, Optional, Union


 
#	WARNING:
#	NOTE:	the kmd.net and kmd.token files are in a folder
#		    named based on the release of kmd - HOWEVER - to date
#		    no easy way has been found to determine the version of kmd
#		    programmatically - find a way or pass the version
#		    as a configuration parameter



import  algosdk                                      #   better type support (not necessary)                
from    algosdk                     import mnemonic                                  
from    algosdk                     import account
from    algosdk.v2client            import algod
from    algosdk.wallet              import Wallet
from    algosdk                     import kmd
from    algosdk.future              import transaction
from    algosdk.future.transaction  import PaymentTxn
from    algosdk.future.transaction  import ApplicationNoOpTxn
from    algosdk.future.transaction  import ApplicationCreateTxn
from    algosdk.future.transaction  import ApplicationOptInTxn
from    algosdk.future.transaction  import ApplicationCloseOutTxn

from error import DopError 

#   class workerAlgorand
#   the following methods have to be implemented
#
#   (x) begin_transaction
#   (x) rollback
#   (x) commit
#   (x) create_user
#   (x) deploy_contract
#   (x) get_wallet_balance
#   (x) subscribe
#   (x) unsubscribe
#   balance                 NOTE:   not in first implementation
#   (x) get_balance         NOTE:   not fully implemented (product related balance)
#   admin_get_grants        NOTE:   not in first implementation - to be moved to chain 2 (offchain)
#   get_receipt             NOTE:   to be removed - to be considered a private/provider specific method
#   set_starting_balance    
#   (x) grant
#   (x) revoke


class workerAlgorand():
    
    def __init__ (self):
        pass


    def begin_transaction(self) -> DopError:
        return DopError(0,"")

    def rollback(self) -> DopError:
        return DopError(0,"")

    def commit(self) -> DopError:
        return DopError(0,"")

    def __wallet_id(
        self,
        wallet_name: str
        ) -> Tuple[str, DopError]:

        """
            returns the wallet id of the wallet named wallet_name
        """
        if self._i_kmd_client == None:
            return "",DopError(2,"Missing value for kmd client.")

        wallets = self._i_kmd_client.list_wallets()
        for arrayitem in wallets:
            if arrayitem.get("name") == wallet_name:
                walletid = arrayitem.get("id")
                return walletid,DopError(0,'')
                break
        return '',DopError(101,"The wallet id for the specified wallet name could not be retrieved.")

    def __account_mnemonic(
        self,
        wallet_name: str,
        wallet_password: str,
        account_address: str
        ) -> Tuple[str, DopError]:

        if self._i_kmd_client == None:
            return "",DopError(2,"Missing value for kmd client.")

        err: DopError
        wallet_id, err = self.__wallet_id(wallet_name)
        if err.isError():
            return "",err

        wallet_handle = self._i_kmd_client.init_wallet_handle(wallet_id, wallet_password)
        account_key = self._i_kmd_client.export_key(wallet_handle, wallet_password, account_address )
        key_mnemonic = mnemonic.from_private_key(account_key)

        #   check for error, exceptions, etc.
        return key_mnemonic, DopError(0,"")




    @staticmethod
    def dop_stateless_create(
        client: algosdk.v2client.algod.AlgodClient
    ,   teal_template_path: str                 #   the absolute path of the teal contract template
    ,   creator_address: str                    #   the address of the creator of the smart contract
        ) -> Tuple[str, DopError]:
        """
            creates the stateless smart contract
            if successful   -> returns the address of the stateless smart contract 
            otherwise       -> returns an empty string
        """

        #   compile the stateless teal prog
        #   set source code 
        #       the source code to be used for this example is DOP/dop.account/dop.account.teal.template
        #       NOTE:   the dop.account.teal (the source code to be compiled) is generated using the file 
        #               dop.account.teal.template by replacing the macro "_RECEIVERADDRESS_" with the "creator_address"
        #               see DOP/dop.account/00_create.sh - that contains the following cmd
        #               sed "s/_RECEIVERADDRESS_/$CREATOR/g" dop.account.teal.template > dop.account.teal


        #   read the template
        teal_template: str = ""
        try:
            with open(teal_template_path, 'r', encoding='utf-8') as f:
                teal_template = f.read()
        except Exception:
            return "",DopError(3,"Teal template file not found.")

        #   now the _RECEIVERADDRESS_ nacro has to be substituted with creator_address
        teal_source = teal_template.replace('_RECEIVERADDRESS_', creator_address)

        
        try:
            compile_response = client.compile(teal_source)
            #   return base64.b64decode(compile_response['result'])
            #   compile_response example
            #   {
            #       'hash': 'LILX6GOG4N6LAOTFT4WW5VTXK5AN4KA5TAN5CYAE7LX5GPC2XXU6NNHDTA', 
            #       'result': 'AyAHAgEABmTIAaCNBiYBIOKaz1eO1YI9t+Lp5CmWTNrK6kvjiZCylN6neTTnB6YYMgQiD0AAKTIEIxJAAAIkQzMAECMSQAAKMwAQJRJAAA0kQzMABygTQAAlIQRDIQVDMwAQIxNAABczARAlE0AADzMBGCQSQAAHMwAIIQYPQyRD'
            #   }
            #   where   'result'    holds the compiled code
            #           'hash'      is the address of the smart contract
        except Exception:
            return "",DopError(4,"Error compiling teal source.")

        smart_contract_address = compile_response['hash']

        #   TODO:   
        #           check if the stateless smart contract needs to be immediately funded
        return smart_contract_address,DopError(0,"")

    @staticmethod
    def dop_stateful_create(
        client: algosdk.v2client.algod.AlgodClient
    ,   teal_clear_program_path: str
    ,   teal_approval_program_path: str
    ,   creator_address: str
    ,   creator_private_key: str
    ,   smart_contract_address: str                     #   address of the stateless smart contract
        ) -> Tuple[str, DopError]:
        """
            creates the stateful smart contract
            if successful   -> returns the txn_id of the stateful smart contract creation transaction
            otherwise       -> returns an empty string
        """

        #ApplicationCreateTxn

        #   get and compile the clear program
        teal_clear_source: str = ""
        try:
            with open(teal_clear_program_path, 'r', encoding='utf-8') as f:
                teal_clear_source = f.read()
        except Exception:
            return "",DopError(5,"Teal clear file not found.")

        compile_response = client.compile(teal_clear_source)            
        clear_program = base64.b64decode(compile_response['result'])


        # declare on_complete as NoOp
        on_complete = transaction.OnComplete.NoOpOC.real

        #   get and compile the approval program
        teal_approval_source: str = ""
        try:
            with open(teal_approval_program_path, 'r', encoding='utf-8') as f:
                teal_approval_source = f.read()
        except Exception:
            return "",DopError(6,"Teal approval file not found.")

        compile_response = client.compile(teal_approval_source) 
        approval_program = base64.b64decode(compile_response['result'])           

        params = client.suggested_params()
        params.flat_fee = True
        params.fee = 1000

        #compile_result = base64.b64decode(compile_response['result'])
        
        smart_contract_arguments = {
            "args":     [smart_contract_address]    #   list of app arguments (goal app create --app-arg)
#       ,   "addrs":    [subscriber_address]        #   list of account arguments
        }

        app_args: list   = workerAlgorand.getArgs(smart_contract_arguments)

        # declare application state storage (immutable)
        local_ints      = 5
        local_bytes     = 5
        global_ints     = 5
        global_bytes    = 5

        # define schema (<class 'algosdk.future.transaction.StateSchema'>)
        global_schema   = transaction.StateSchema(global_ints, global_bytes)
        local_schema    = transaction.StateSchema(local_ints, local_bytes)

        unsigned_txn = ApplicationCreateTxn(creator_address, params, on_complete, approval_program, clear_program, global_schema, local_schema, app_args)
        # sign transaction
        signed_txn = unsigned_txn.sign(creator_private_key)
        txn_id = signed_txn.transaction.get_txid()

        #   send transaction
        try: 
            client.send_transactions([signed_txn])    
        except Exception as err:
            return txn_id, DopError(120, f"An error occurred while creating stateful \
                smart contract.")
        return (txn_id,DopError(0,""))

    @staticmethod
    def mnemonic_to_private_key(mnemonic_key: str) -> Tuple[str, DopError]:
        """
        convert a menmonic key into a "single string" private key
        """
        private_key: str = ""
        try:
            private_key = mnemonic.to_private_key(mnemonic_key)
        except Exception:
            return "",DopError(10,"Mnemonic could not be converted to private key.")

        return private_key,DopError(0,"")


    
    #   private method
    def __algorand_smart_contract_create(
        self
    ,   client: algosdk.v2client.algod.AlgodClient
    ,   creator_mnemonic: str
        ) -> Tuple[str, str, DopError]:
        
        """
            the DOP smart contract is a linked smart contract
            (there is a stateless part, to represent the smart contract account
            and a stateful part, holding the DOP logic)
            RETURNS:    
                    address of the stateless smart contract
                    app index of the stateful smart contract
                    DopError

            see https://developer.algorand.org/docs/get-details/dapps/smart-contracts/frontend/apps/?from_query=call%20smart%20contract%20from%20javascript#call-noop
            see https://github.com/algorand/py-algorand-sdk/blob/5b496e0928af1dcae4e393693421f590a6111907/algosdk/future/transaction.py
            see https://developer.algorand.org/docs/rest-apis/algod/v2/
        """

        err: DopError
        creator_private_key: str

        creator_private_key, err = self.mnemonic_to_private_key(creator_mnemonic)
        if err.isError():
            return ("",0,err)
        creator_address       = account.address_from_private_key(creator_private_key)         #   this line to be deleted

        smart_contract_address, err = self.dop_stateless_create(client, self._i_stateless_teal_template_path, creator_address)
        if err.isError():
            return ("",0,err)

        txn_id, err = self.dop_stateful_create(client, self._i_teal_clear_program_path, self._i_teal_approval_program_path, creator_address, creator_private_key, smart_contract_address)

        if err.isError():
            return "",0,err

        # await confirmation
        confirmed_txn = self.wait_for_confirmation(client, txn_id, 4)  


        #   confirmed_txn holds:
        #   {
        #       'application-index': 392, 
        #       'confirmed-round': 66118, 
        #       'global-state-delta': [
        #                               {'key': 'a2V5', 'value': {'action': 1, 'bytes': 'MHgwMA=='}}, 
        #                               {'key': 'a2lk', 'value': {'action': 1, 'bytes': 'MHgwMA=='}}, 
        #                               {'key': 'bGlua2Vk', 'value': {'action': 1, 'bytes': 'RjZWVkZNTEY1RVM0S1VZTUg3TFlGVlZLRUFUQlJMQjdHRllSMk1IQkRCWEpOM1pHUURZUUVNUEE3UQ=='}}, 
        #                               {'key': 'Y3JlYXRvcg==', 'value': {'action': 1, 'bytes': 'tpw3hll7wAFNFzreNA5uPoRnNAnJ28KBEYxhgtJW4to='}}
        #                               ], 
        #       'pool-error': '', 
        #       'sender-rewards': 16230, 
        #       'txn': {'sig': 'NiAHaHCPSs/APuWMBvpmfiG1iYDod0RzeRZd2YzFSCQ+mfwVGgH5MEE1oxJ4f7VVOIoSpaEZTRu1uKlXOnadAQ==', 
        #               'txn': {'apaa': ['RjZWVkZNTEY1RVM0S1VZTUg3TFlGVlZLRUFUQlJMQjdHRllSMk1IQkRCWEpOM1pHUURZUUVNUEE3UQ=='], 
        #                       'apap': 'BSAGAAECBucJZCYMA2tpZANrZXkFZ3JhbnQGZXJyPTA7DHN1YnNjcmlwdGlvbgE7B2NyZWF0b3IGZ2V0a2V5CGVycj0yNTU7BGtleT0GbGlua2VkBDB4MDAxGCISQAGSMRkjEkABpDEZJBJAAaAxGYEFEkABkjIEIxJAAAkyBCQSQAFQIkMxECUTQAGEJwZkMQASQAChNhoAgAlzdWJzY3JpYmUSQAAjNhoAgAt1bnN1YnNjcmliZRJAABw2GgAnBxJAABwnCLAhBEMiJwQjZiIqImaB6AdDIicEImaB8gdDIicEYiMTQAApIipiIxNAAC02GgEoZBNAADAiKChkZiIpKWRmK7AnCSlkUCcFULAhBUOABmVycj0xO7CBZUOABmVycj0yO7CBZkOABmVycj0zO7CBZ0M2GgAqEkAAbTYaAIAGcmV2b2tlEkAAaDYaAIAGY2hhcmdlEkAAYzYaAIAGc2V0a2V5EkAAWDYaACcHEkAABicIsCEEQzYaAShkE0AAGyuwJwkpZFAnBVCwgARraWQ9KGRQJwVQsCEFQ4AHZXJyPTEwO7CBbkMjKiNmK7CB0A9DIyoiZiuwgdoPQ4HkD0MpNhoBZyg2GgJnK7CB7g9DMwAQIxNAADUzARAlE0AALTMABycKZBNAACOB9ANDJwYxAGcnCjYaAGcpJwtnKCcLZ4EKQ4EUQ4EeQ4EoQyJD', 
        #                       'apgs': {'nbs': 5, 'nui': 5}, 
        #                       'apls': {'nbs': 5, 'nui': 5}, 
        #                       'apsu': 'AyABASI=', 
        #                       'fee': 1000, 
        #                       'fv': 66017, 
        #                       'gen': 'private-v1', 
        #                       'gh': '85lTOmM+7boPryKD0hCIWMkcoKAZZaFZ+Gi9YSitq0g=', 
        #                       'lv': 67017, 
        #                       'snd': 'W2ODPBSZPPAACTIXHLPDIDTOH2CGONAJZHN4FAIRRRQYFUSW4LNODF4EVY', 
        #                       'type': 'appl'}
        #               }
        #       }


        # display results
        transaction_response = client.pending_transaction_info(txn_id)

        #   transaction_response
        #   {
        #       'application-index': 392, 
        #       'confirmed-round': 66118, 
        #       'global-state-delta': [
        #                               {
        #                                   'key': 'Y3JlYXRvcg==', 
        #                                   'value': {'action': 1, 'bytes': 'tpw3hll7wAFNFzreNA5uPoRnNAnJ28KBEYxhgtJW4to='}
        #                               }, 
        #                               {
        #                                   'key': 'a2V5', 
        #                                   'value': {'action': 1, 'bytes': 'MHgwMA=='}
        #                               }, 
        #                               {
        #                                   'key': 'a2lk', 
        #                                   'value': {'action': 1, 'bytes': 'MHgwMA=='}
        #                               }, 
        #                               {
        #                                   'key': 'bGlua2Vk', 
        #                                   'value': {'action': 1, 'bytes': 'RjZWVkZNTEY1RVM0S1VZTUg3TFlGVlZLRUFUQlJMQjdHRllSMk1IQkRCWEpOM1pHUURZUUVNUEE3UQ=='}
        #                               }
        #                               ], 
        #       'pool-error': '', 
        #       'sender-rewards': 16230, 
        #       'txn': {
        #                   'sig': 'NiAHaHCPSs/APuWMBvpmfiG1iYDod0RzeRZd2YzFSCQ+mfwVGgH5MEE1oxJ4f7VVOIoSpaEZTRu1uKlXOnadAQ==', 
        #                   'txn': {
        #                               'apaa': ['RjZWVkZNTEY1RVM0S1VZTUg3TFlGVlZLRUFUQlJMQjdHRllSMk1IQkRCWEpOM1pHUURZUUVNUEE3UQ=='], 
        #                               'apap': 'BSAGAAECBucJZCYMA2tpZANrZXkFZ3JhbnQGZXJyPTA7DHN1YnNjcmlwdGlvbgE7B2NyZWF0b3IGZ2V0a2V5CGVycj0yNTU7BGtleT0GbGlua2VkBDB4MDAxGCISQAGSMRkjEkABpDEZJBJAAaAxGYEFEkABkjIEIxJAAAkyBCQSQAFQIkMxECUTQAGEJwZkMQASQAChNhoAgAlzdWJzY3JpYmUSQAAjNhoAgAt1bnN1YnNjcmliZRJAABw2GgAnBxJAABwnCLAhBEMiJwQjZiIqImaB6AdDIicEImaB8gdDIicEYiMTQAApIipiIxNAAC02GgEoZBNAADAiKChkZiIpKWRmK7AnCSlkUCcFULAhBUOABmVycj0xO7CBZUOABmVycj0yO7CBZkOABmVycj0zO7CBZ0M2GgAqEkAAbTYaAIAGcmV2b2tlEkAAaDYaAIAGY2hhcmdlEkAAYzYaAIAGc2V0a2V5EkAAWDYaACcHEkAABicIsCEEQzYaAShkE0AAGyuwJwkpZFAnBVCwgARraWQ9KGRQJwVQsCEFQ4AHZXJyPTEwO7CBbkMjKiNmK7CB0A9DIyoiZiuwgdoPQ4HkD0MpNhoBZyg2GgJnK7CB7g9DMwAQIxNAADUzARAlE0AALTMABycKZBNAACOB9ANDJwYxAGcnCjYaAGcpJwtnKCcLZ4EKQ4EUQ4EeQ4EoQyJD', 
        #                               'apgs': {'nbs': 5, 'nui': 5}, 
        #                               'apls': {'nbs': 5, 'nui': 5}, 
        #                               'apsu': 'AyABASI=', 
        #                               'fee': 1000, 
        #                               'fv': 66017, 
        #                               'gen': 'private-v1', 
        #                               'gh': '85lTOmM+7boPryKD0hCIWMkcoKAZZaFZ+Gi9YSitq0g=', 
        #                               'lv': 67017, 
        #                               'snd': 'W2ODPBSZPPAACTIXHLPDIDTOH2CGONAJZHN4FAIRRRQYFUSW4LNODF4EVY', 
        #                               'type': 'appl'
        #                           }
        #               }
        #       }

        app_id = transaction_response['application-index']
        return (smart_contract_address, str(app_id), DopError(0,""))


    #   private method
    def __account_send(self, from_mnemonic, to_address, amount) -> Tuple[str,DopError]:

        """
        Sends tokens from one account to another
        """
        if self._i_algod_client == None:
            return "",DopError(1,"Missing value for algod client.")

        params = self._i_algod_client.suggested_params()
        params.flat_fee = True
        params.fee = 1000
        txn_note = "DOP OPTIN".encode()

        err: DopError

        from_private_key, err = self.mnemonic_to_private_key(from_mnemonic)
        if err.isError():
            return "",err
        from_address = account.address_from_private_key(from_private_key)

        
        params = self._i_algod_client.suggested_params()
        # comment out the next two (2) lines to use suggested fees
        params.flat_fee = True
        params.fee = 1000
        txn_note = "DOP funds".encode()

        #   create an unsigned transaction
        unsigned_txn = PaymentTxn(from_address, params, to_address, amount, None, txn_note)

        #   sign the transaction using the private key of the sender (from_address)
        signed_txn = unsigned_txn.sign(from_private_key)

        #submit transaction
        txid = self._i_algod_client.send_transaction(signed_txn)
        print("Successfully sent transaction with txID: {}".format(txid))

        # wait for confirmation 
        try:
            confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  
        except Exception as err:
            print(err)
            return "", DopError(301,'An exception occurred while waiting \
                for the confirmation of the send transaction.')
        
        return txid, DopError(0,)
    
    @staticmethod
    def wait_for_confirmation(
        client: algosdk.v2client.algod.AlgodClient
    ,   transaction_id: str
    ,   timeout: int
    ):
        """
        Wait until the transaction is confirmed or rejected, or until 'timeout'
        number of rounds have passed.
        Args:
            transaction_id (str): the transaction to wait for
            timeout (int): maximum number of rounds to wait    
        Returns:
            dict: pending transaction information, or throws an error if the transaction
                is not confirmed or rejected in the next timeout rounds
        """
        start_round = client.status()["last-round"] + 1
        current_round = start_round

        while current_round < start_round + timeout:
            try:
                pending_txn = client.pending_transaction_info(transaction_id)
            except Exception:
                return 
            if pending_txn.get("confirmed-round", 0) > 0:
                return pending_txn
            elif pending_txn["pool-error"]:  
                raise Exception(
                    'pool error: {}'.format(pending_txn["pool-error"]))
            client.status_after_block(current_round)                   
            current_round += 1
        raise Exception(
            'pending tx not found in timeout rounds, timeout value = : {}'.format(timeout))

    @staticmethod
    def Token(token: str, path: str) -> Tuple[DopError, str]:
        ntoken: str = token
        if ntoken == '':
            try:
                with open(path, 'r') as f:
                    ntoken = f.readline()
            except Exception as e:
                #print(str(e))
                return (DopError(20,"An exception occurred while reading token file."),ntoken)

            l: list = ntoken.split('\n')
            ntoken = l[0]
        return (DopError(), ntoken)

    @staticmethod 
    def Port(port: str, path: str) -> Tuple[DopError, str]:
        nport: str = port
        host: str = ''
        if nport == '':
            try:
                with open(path, 'r') as f:
                    host = f.readline()
            except:
                return (DopError(21,"An exception occurred while reading port file."),nport)

        l: list = host.split('\n')
        host = l[0]
        l = host.split(':')
        if len(l) > 1:
            nport = l[1]

        return (DopError(), nport)
        
    def algodToken(self) -> Tuple[DopError, str]:
        """
        returns the token of necessary to connect to the algod node
        NOTE:   the token is retrieved by reading and parsing the file "$ALGORAND_DATA/algod.token"
                so this function requires the macro ALGORAND_DATA to be defined and available
                to the process calling this method
        """

        token: str
        if 'atoken' in self._i_config:
            #   atoken passed in connstring - ignore file containing token
            token = self._i_config['atoken']
            self._i_algo_token = token
            return DopError(),token

        err, token = self.Token(self._i_algo_token, self._i_algo_token_file)
        if err.code == 0:
            self._i_algo_token = token

        return (err,token)

    def algodPort(self) -> Tuple[DopError, str]:
        """
        returns the TCP port the algod node is listening to
        NOTE:   the port is retrieved by reading and parsing the file "$ALGORAND_DATA/algod.net"
                so this function requires the macro ALGORAND_DATA to be defined and available
                to the process calling this method
        """
        port: int
        if 'anetprt' in self._i_config:
            #   anetprt passed in connstring - ignore file containing port
            port = int(self._i_config['anetprt'])
            self._i_algo_port = port
            return DopError(),port

        err, port = self.Port(self._i_algo_port, self._i_algo_net_file)
        if err.code == 0:
            self._i_algo_port = port
        return (err, port)

    def kmdToken(self) -> Tuple[DopError, str]:
        token: str
        if 'ktoken' in self._i_config:
            #   atoken passed in connstring - ignore file containing token
            token = self._i_config['ktoken']
            self._i_kmd_token = token
            return DopError(),token

        err, token = self.Token(self._i_kmd_token, self._i_kmd_token_file)
        if err.code == 0:
            self._i_kmd_token = token
        return (err, token)

    def kmdPort(self) -> Tuple[DopError, str]:
        port: int
        if 'knetprt' in self._i_config:
            #   anetprt passed in connstring - ignore file containing port
            port = int(self._i_config['knetprt'])
            self._i_kmd_port = port
            return DopError(),port

        err, port = self.Port(self._i_kmd_port, self._i_kmd_net_file)
        if err.code == 0:
            self._i_kmd_port = port
        return (err, port)

    def kmd(self) -> Tuple[DopError, algosdk.kmd.KMDClient]:
        err, kmd_token = self.kmdToken()
        if err.code != 0:
            return (err,None)
        err, kmd_port = self.kmdPort()
        if err.code != 0:
            return (err,None)

        kmd_ip_address: str = 'http://localhost:' 
        if 'knetip' in self._i_config:
            kmd_ip_address = 'http://' + self._i_config['knetip'] + ':'
        kmd_address = kmd_ip_address + str(kmd_port)

        kcl = kmd.KMDClient(kmd_token, kmd_address)

        try:
            #   NOTE:           it seems that the kmd can be instantiated only if using localhost
            #                   to be checked with algorand
            kcl.versions()  #   generates an exception if the kcl is not connected
        except Exception:
            return(DopError(22, "An exception occurred while initializing kmd client."),kcl)

        return(DopError(),kcl)
    
    def algod(self) -> Tuple[DopError, algosdk.v2client.algod.AlgodClient]:
        #   get algod token
        err, algod_token = self.algodToken()
        if err.code != 0:
            return (err,None)
        #   get algod port
        err, algod_port = self.algodPort()
        if err.code != 0:
            return (err,None)
        #   get algo node address (default is localhost)

        algod_ip_address: str = 'http://localhost:' 
        if 'anetip' in self._i_config:
            algod_ip_address = 'http://' + self._i_config['anetip'] + ':'
        #algod_address = 'http://localhost:' + str(algod_port)
        algod_address = algod_ip_address + str(algod_port)
        algocl = algod.AlgodClient(algod_token, algod_address)

        #   check if the algod client is valid
        try:
            algocl.status()
        except Exception:
            return(DopError(23, "Error in initializing algod client."),algocl)

        return(DopError(),algocl)

    @staticmethod
    def getArgs(argsobj: dict) -> list:
        args = argsobj.get("args")

        if args==None:
            return None

        if len(args) < 1:
            return None

        b_args: list = []
        for item in args:
            b_args.append(bytes(item,'utf-8'))
        return b_args

    @staticmethod
    def getAccounts(argsobj: dict) -> list:
        args = argsobj.get("addrs")

        if args==None:
            return None

        if len(args) < 1:
            return None

        return args

    def dopSmartContract(
        self
    ,   algod_client: algosdk.v2client.algod.AlgodClient
    ,   appid:  int                     #   smart contract index (address)
    ,   owner_mnemonic: str             #   private key (mnemonic) of the owner of the smart contract
    ,   scarguments: dict               #   {"args":[argslist], "addrs":[accountaddresseslist]}
    ,   transaction_note: str           #   the note field withon the transaction
    ) -> Tuple[str, DopError]:               #   error code, transaction id

        #   retrieve and change suggested params (for the transaction)        
        #   this could become an argument, to be investigated (future releases)
        params = algod_client.suggested_params()
        params.flat_fee = True
        params.fee = 1000

        txn_note = transaction_note.encode()

        err: DopError
        owner_private_key: str
        owner_private_key,err   = self.mnemonic_to_private_key(owner_mnemonic)
        if err.isError():
            return "",err

        owner_address       = account.address_from_private_key(owner_private_key)         #   this line to be deleted

        arguments_list   = self.getArgs(scarguments)
        accounts_list    = self.getAccounts(scarguments)

        unsigned_txn = ApplicationNoOpTxn(owner_address, params, appid, arguments_list, accounts_list, None, None, txn_note)
        signed_txn = unsigned_txn.sign(owner_private_key)

        txid = ''
        try:
            txid = algod_client.send_transaction(signed_txn)
            #   print("Successfully sent transaction with txID: {}".format(txid))

        except Exception as err:
            #print(err)
            return "", DopError(202,f"An exception occurred when sending transaction.")

        return(txid, DopError(0,""))      #   now the transaction can be waited for

    def __default(self):
        #   set default parameters
        self._i_algo_token      = ''
        self._i_algo_port       = ''
        self._i_algod_client    = None

        self._i_kmd_token       = ''
        self._i_kmd_port        = ''
        self._i_kmd_client      = None

        self._i_config: dict   = {}
        
        algorand_data_path: str = '/home/ecosteer/dop/externals/algorand/net1/Primary'
        if 'ALGORAND_DATA' in os.environ:
            algorand_data_path = os.environ['ALGORAND_DATA']

        self._i_algo_token_file     = algorand_data_path + '/algod.token'           #   this has to go
        self._i_config['atokf']     = algorand_data_path + '/algod.token'

        self._i_algo_net_file       = algorand_data_path + '/algod.net'             #   this has to go
        self._i_config['anetf']     = algorand_data_path + '/algod.net'

        self._i_kmd_token_file      = algorand_data_path + '/kmd-v0.5/kmd.token'    #   this has to go
        self._i_config['ktokf']     = algorand_data_path + '/kmd-v0.5/kmd.token'

        self._i_kmd_net_file        = algorand_data_path + '/kmd-v0.5/kmd.net'      #   this has to go
        self._i_config['knetf']     = algorand_data_path + '/kmd-v0.5/kmd.net'
        

        dop_smart_contract_root_path: str = '/home/ecosteer/dop/intermediation/algorand/DOP'
        self._i_config['scrf'] = dop_smart_contract_root_path

        user_wallet: str            = "unencrypted-default-wallet"                  # wallet where the users are created
        user_wallet_password: str   = ""                                            # password to access the wallet
        self._i_config['usrwlab']   = user_wallet
        self._i_config['usrwpwd']   = user_wallet_password


        if 'DOP_SMART_CONTRACT_ROOT_FOLDER' in os.environ:
            dop_smart_contract_root_path = os.environ['DOP_SMART_CONTRACT_ROOT_FOLDER']
            
        self._i_stateless_teal_template_path    = dop_smart_contract_root_path + '/dop.account/dop.account.teal.template'
        self._i_config['sttp'] = 'dop.account/dop.account.teal.template'
        self._i_teal_approval_program_path      = dop_smart_contract_root_path + '/dop.stateful/dop.stateful.teal'
        self._i_config['tapp'] = 'dop.stateful/dop.stateful.teal'
        self._i_teal_clear_program_path         = dop_smart_contract_root_path + '/dop.clear/basicClear.teal'
        self._i_config['tcpp'] = 'dop.clear/basicClear.teal'

        self._i_config['ownmne'] = ''


    #============================================================================
    #   abstract methods
    #============================================================================
    #   NOTE:   init must become an abstract method
    def init(self, constring: str) -> DopError:

        self.__default()
                
        #   convert connstring into a dict (see config_to_dict in shared.utils.py)
        temp_config: dict = {}

        temp_list: list = constring.split(';')
        for el in temp_list:
            ell = el.split('=')
            if len(ell) != 2:
                continue
            temp_config[ell[0]]=ell[1]

        pars: list = [
            'atokf',
            'anetf',
            'ktokf',
            'knetf',
            'atoken',
            'anetprt',
            'anetip',
            'ktoken',
            'knetprt',
            'knetip',
            'scrf',
            'sttp',
            'tapp',
            'tcpp',
            'usrwlab',
            'usrwpwd',
            'ownmne'
            ]

        for p in pars:
            if p in temp_config:
                self._i_config[p] = temp_config[p]


        
        #   connection string parameters
        #   label   type        logic
        #   ------+---------+------------------------------------------------------------------------------------------------
        #   atokf   string      absolute path of the algod.token file
        #   anetf   string      absolute path of the algod.net file     
        #   ktokf   string      absolute path of the kmd.token file
        #   knetf   string      absolute path of the kmd.net file
        #   atoken  string      algod token (if this is defined then atokf will not be used)
        #   anetprt int         algod tcp ip port (if this is defined then the anetf will not be used - anetip required)
        #   anetip  string      algod tcp ip address (if this is defined then the anetf will not be used - anetprt required)
        #   ktoken  string      kmd token (if this is defined then atokf will not be used)
        #   knetprt int         kmd tcp ip port (if this is defined then the knetf will not be used - knetip required)
        #   knetip  string      kmd tcp ip address (if this is defined then the knetf will not be used - knetprt required)
        #   scrf    string      smart contract root folder      : absolute path of the folder containing sttp, atpt and tcpp
        #   sttp    string      stateless teal template path    : relative path of the stateless teal template
        #   tapp    string      teal approval program path      : relative path of the teal approval program
        #   tcpp    string      teal clear program path         : relative path of the teal clear program
        #	usrwlab	string		user wallet (the wallet used by the worker to create accounts)
		#	usrwpwd	string		user wallet password

        #   ownmne  string      mnemonic of the owner account to be used to fund newly created accounts

        #   example 1 (can be used only if the kmd and algod are running on localhost)
        #   atokf=/home/ecosteer/algorand/net1/Primary/algod.token;anetf=/home/ecosteer/algorand/net1/Primary/algod.net;\
        #   ktokf=/home/ecosteer/algorand/net1/Primary/kmd.token;knetf=/home/ecosteer/algorand/net1/Primary/kmd.net;\
        #   scrf=/home/ecosteer/algorand/smartcontracts/DOP;\
        #   sttp=dop.account/dop.account.teal.template;\
        #   tapp=dop.stateful/dop.stateful.teal;\
        #   tcpp=dop.clear/basicClear.teal;

        #   example 2 (to be used if the kmd and algod are running on a remote host)
        #   atoken=45d2689bb4b555b757b00972d82c0a872f7b2aa136a5351768280dbe7cf2e9b2;\
        #   anetprt=18445;\
        #   anetip=192.178.20.30;\
        #   ktoken=d278689bb4b555b7502030465782c0a872f7b2aa136a5351768280dbe7cf2ab90;\
        #   knetprt=18435;\
        #   knetip=192.178.20.30;\
        #   scrf=/home/ecosteer/algorand/smartcontracts/DOP;\
        #   sttp=dop.account/dop.account.teal.template;\
        #   tapp=dop.stateful/dop.stateful.teal;\
        #   tcpp=dop.clear/basicClear.teal;

        #   test only
        for el in self._i_config:
            print(el + ':[' + self._i_config[el] + ']')
        
        return DopError(0, "")

    def open(self) -> DopError:
        """
            open the algod client and the kmd client
            the following properties are valorized:
            1)  _i_algod_token
            2)  _i_algod_port
            3)  _i_kmd_token
            4)  _i_kmd_port
        """


        #   self.algod
        #   sets self._i_algod_token and self._i_algod_port
        err, self._i_algod_client = self.algod()
        if err.isError():
            return err

        err, self._i_kmd_client = self.kmd()
        if err.isError():
            return err

        if 'ownmne' in self._i_config: 
            self._own_mnemonic = self._i_config['ownmne']
        else:
            self._own_mnemonic = None
            return DopError(201, "Owner mnemonic not provided.")

        return err

    def close(self) -> DopError:
        #   TODO:   check if algod and kmd client have to be "closed" 
        return DopError(0,"")


    def get_balance(self,
                    publisher_address: str,                         #   EoA address of the publisher (contract owner)
                    subscriber_address: str,                        #   EoA address of the subscriber we want to check the balance 
                    contract_address: str) -> Tuple[dict, DopError]:   #   address (blockchain layer) of the contract) -> Tuple[dict, DopError]:
        """
        in this version this method is not "really" implemented
        """
        response = {}
        response['subscribed'] = 1
        response['granted'] = 1             #   shortcut - use sub_keyget to valorize this field or use DB
        response['credit'] = 100
        response['debit'] = 0

        return response, DopError(0,"")

    def create_user(self, username: str, password: str) -> Tuple[str, str, DopError]: 
        """
            creates a blockchain account and returns the address (public key) of the account and the password
            of the account (ethereum: input password, algorand, generated private key)

        """
        user_address = ""
        wallet_id: str
        err: DopError

        wallet_name = self._i_config['usrwlab']
        wallet_password = self._i_config['usrwpwd']

        wallet_id, err = self.__wallet_id(wallet_name)
        if err.isError():
            return "","",err

        
        try:
            wallet = Wallet(wallet_name, wallet_password, self._i_kmd_client)
            #   create the account
            account_address     = wallet.generate_key()
            account_mnemonic, err    = self.__account_mnemonic(wallet_name,wallet_password,account_address)
            if err.isError():
                return "","",err
            #   return err=0,account_address
            return account_address, account_mnemonic,DopError(0,"")

        except Exception as err:
            #   likely the password is wrong
            print(err)      #   logging etc.
            return "","",DopError(203,"An exception occurred while creating user.")

        return "","",DopError(1000,"")             # never hit


        return (user_address,user_mnemonic,DopError(0,""))
    


    def get_wallet_balance(self, account_address: str, currency="algo") -> Tuple[str, DopError]:
        """
            TODO:       return account_balance, DopError (as usual)
            TODO:       the method name should be change into "get_account_balance" to disambiguate between account and wallet
            NOTE:       the abstract was defined with a str return value
        """
        if self._i_algod_client == None:
            return "", DopError(1,"Missing value for algod client.")

        try:
            #   address is the account address - for instance: "4KNM6V4O2WBD3N7C5HSCTFSM3LFOUS7DRGILFFG6U54TJZYHUYMDPN26KY"
            from_account_info = self._i_algod_client.account_info(account_address)
            #   the account balance is in micro algos
            account_balance = from_account_info.get('amount')
            #print("Origin Account balance     : [{} microAlgos]".format(from_account_info.get('amount')))
            return account_balance, DopError(0,"")
        except Exception:
            return "",DopError(204,"An exception occurred while getting wallet balance.")

        
    def deploy_contract(self,
                        publisher_address: str,                 #   address of the owner account
                        secret: str,                            #   secret for the owner account (algorand: private key mnemonic of the owner)
                        tariff_period: int,                     #   period of the tariff 
                        tariff_price: int                       #   price of a period
                        ) -> Tuple[Optional[str], DopError]:
        """
            NOTE:
                The abstract method returns a transaction hash that is inserted into the 
                rdbms (transactions schema) - as this is typically a pending operation finalized by an event emitted by the monitor.
                For Algorand: this might require a complete different logic of the processor "product_create.py" - possibly a 
                processor specific for Algorand will have to be implemented.
                See also monitor_des.py - it processes the event (DEPLOY_CONTRACT) that is
                meant to close the pending op

                NOTE:   EnableDeveloperAPI must be set to true (node configuration file)
                NOTE:   https://developer.algorand.org/docs/run-a-node/reference/config/

                TODO:   review static and private method dop_stateful/dop_stateless/__algorand_smart_contract_create
        """

        #   publisher_address:      not used
        #   tariff_period:          not used (for future release)
        #   tariff_price:           not used (for future release)
        #   secret: is the mnemonic of the publisher
        
        smart_contract_address: str     #   the address of the stateless smart contract (the smart contract linked to the stateful smart contract)
                                        #   as the previously defined abstract method allows tp return just two values
                                        #   we will not return the smart contract address for the moment - to be checked
                                        #   in this release the smart_comtract_address will be encoded using the following string:
                                        #   %smart_contract_adress%@%app_id

        app_id: str                     #   the application id (this id will have to be used for invoking the smart contract)
        err: DopError

        if self._i_algod_client == None:
            #   must open before
            return ("",DopError(1,"Missing value for algod client."))

        smart_contract_address, app_id, err = self.__algorand_smart_contract_create(self._i_algod_client, secret) 
        if err.isError():
            return "", err
        #   TODO check if stateless contract has to be funded
        encoded_smart_contract_address: str = smart_contract_address + '@' + str(app_id)
        return (encoded_smart_contract_address, err)

    def algorand_sub_optin(     #   ALGORAND SPECIFIC
        self,
        from_mnemonic: str,         #   mnemonic (secret) of the account that is opting in
        application_address: str    #   application index of the smart contract the account wants to opt into
        ) -> DopError:
        """
        Algorand specific (an account has to optin before subscribing to a smart contract)
        this methid can be called by a specific Algorand processor provider (not an abstract method),
        for instance by the processor provider that implement the subscription logic
        SO: it has not be implemented as a private method - but an Algorand specific method.

        NOTE:   the subscriber, before subscribing the contract X, MUST opt-in to the contract X
        """
        #   see 01_sub_optin.py
        
        if self._i_algod_client == None:
            return DopError(1,"Missing value for algod client.")

        params = self._i_algod_client.suggested_params()
        params.flat_fee = True
        params.fee = 1000
        txn_note = "DOP OPTIN".encode()

        err: DopError

        #subscriber_private_key = mnemonic.to_private_key(from_mnemonic)
        subscriber_private_key, err = self.mnemonic_to_private_key(from_mnemonic)
        if err.isError():
            return err
        subscriber_address = account.address_from_private_key(subscriber_private_key)

        appid = int(application_address)
        unsigned_txn = ApplicationOptInTxn(subscriber_address, params, appid, None, None, None, None, txn_note)
        signed_txn = unsigned_txn.sign(subscriber_private_key)

        txid =''
        try:
            txid = self._i_algod_client.send_transaction(signed_txn)
            #   print("Successfully sent transaction with txID: {}".format(txid))

        except Exception as err:
            #   print(err)
            return DopError(205,"An exception occurred when sending optin transaction.")

        try:
            confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  
            #   TODO: confirmed_txn can be used to provide detailed log, see next
            #   commented lines
            #   print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
            #   print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

        except Exception as err:
            #   print(err)
            return DopError(302,"An exception occurred while waiting for confirmation of optin transaction.")

        return DopError(0,"")


    def algorand_sub_optout(     #   ALGORAND SPECIFIC
        self,
        from_mnemonic: str,         #   mnemonic (secret) of the account that is opting in
        application_address: str    #   application index of the smart contract the account wants to opt into
        ) -> DopError:
        """
        Algorand specific (symmetric to algorand_sub_optin)
        NOTE:   a subscriber that has unsubscribed should call optout, too
        """
        
        if self._i_algod_client == None:
            return DopError(1,"Missing value for algod client.")

        params = self._i_algod_client.suggested_params()
        params.flat_fee = True
        params.fee = 1000
        txn_note = "DOP OPTOUT".encode()

        err: DopError
        subscriber_private_key: str

        subscriber_private_key, err = self.mnemonic_to_private_key(from_mnemonic)
        if err.isError():
            return err
        subscriber_address = account.address_from_private_key(subscriber_private_key)

        appid = int(application_address)
        unsigned_txn = ApplicationCloseOutTxn(subscriber_address, params, appid, None, None, None, None, txn_note)
        signed_txn = unsigned_txn.sign(subscriber_private_key)

        txid =''
        try:
            txid = self._i_algod_client.send_transaction(signed_txn)
            #   print("Successfully sent transaction with txID: {}".format(txid))

        except Exception as err:
            #   print(err)
            return DopError(206,"An exception occurred when sending optout transaction.")

        try:
            confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  
            #   TODO: confirmed_txn can be used to provide detailed log, see next
            #   commented lines
            #   print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
            #   print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

        except Exception as err:
            #   print(err)
            return DopError(303,"An exception occurred while waiting for \
                        confirmation of optout transaction.")

        return DopError(0,"")


    def subscribe(self,
                  subscriber_addr: str,             #   subscriber address
                  subscriber_psw: str,              #   private key mnemonic
                  contract_address: str,            #   algorand application index
                  secret: str                       #   not used in this release
                  ) -> Tuple[str, DopError]:  
        """
        Subscribe to a contract
        """

        if self._i_algod_client == None:
            return "",DopError(1,"")        #   must be connected to a node

        params = self._i_algod_client.suggested_params()
        params.flat_fee = True
        params.fee = 1000
        txn_note = "DOP SUBSCRIBE".encode()

    #   the transaction type that has to be sent is of type ApplicationNoOpTxn
    #   see https://github.com/algorand/py-algorand-sdk/blob/5ca32cea62168ae339ccfdfbefaa6bc6ac094052/algosdk/future/transaction.py#L2040
    #   line 2040
        
        err: DopError
        subscriber_private_key: str

        subscriber_private_key, err = self.mnemonic_to_private_key(subscriber_psw)
        if err.isError():
            return "",err

        subscriber_address = account.address_from_private_key(subscriber_private_key)

        app_args : list = []
        app_args.append(bytes('subscribe','utf-8'))
        unsigned_txn = ApplicationNoOpTxn(subscriber_address, params, contract_address, app_args, None, None, None, txn_note)
        signed_txn = unsigned_txn.sign(subscriber_private_key)

        txid = ''
        try:
            txid = self._i_algod_client.send_transaction(signed_txn)
            #print("Successfully sent transaction with txID: {}".format(txid))

        except Exception as err:
            #print(err)
            return "", DopError(207,"An exception occurred when sending subscribe transaction.")

        # wait for confirmation 
        try:
            confirmed_txn = self.wait_for_confirmation(self._i_algod_client,txid,4)

            #print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
            #   print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

        except Exception as err:
            #print(err)
            return "",DopError(304,"An exception occurred while waiting for confirmation \
                    of subscribe transaction.")

        return txid,DopError(0,"")


    def unsubscribe(self, 
                    subscriber_addr: str,               #   not used
                    subscriber_psw: str,                #   subscriber account private key mnemonic
                    contract_address: str             #   application index
                    #,secret: str                         #   not used 
                    ) -> Tuple[str, DopError]:
            """
            UnSubscribe from a contract
            return transaction id
            """

            if self._i_algod_client == None:
                return "",DopError(1,"Missing value for algod client.")        #   must be connected to a node

            params = self._i_algod_client.suggested_params()
            params.flat_fee = True
            params.fee = 1000
            txn_note = "DOP UNSUBSCRIBE".encode()

            err: DopError
            subscriber_private_key: str
            subscriber_private_key, err = self.mnemonic_to_private_key(subscriber_psw)
            if err.isError():
                return "",err
            subscriber_address = account.address_from_private_key(subscriber_private_key)

            application_index = int(contract_address)

            app_args : list = []
            app_args.append(bytes('unsubscribe','utf-8'))
            unsigned_txn = ApplicationNoOpTxn(subscriber_address, params, application_index, app_args, None, None, None, txn_note)
            signed_txn = unsigned_txn.sign(subscriber_private_key)

            txid = ''
            try:
                txid = self._i_algod_client.send_transaction(signed_txn)
                #print("Successfully sent transaction with txID: {}".format(txid))

            except Exception as err:
                #print(err)
                return "", DopError(208,'An exception occurred when sending unsubscribe transaction.')

            # wait for confirmation 
            try:
                confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  

                #print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
                #print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

            except Exception as err:

                return "",DopError(305,'An exception occurred while waiting for \
                            confirmation of unsubscribe transaction')

            return txid,DopError(0,'')


    def grant(self,
              publisher_address: str,       #   not used
              publisher_passw: str,         #   publisher private key mnemonic
              contract_address: str,        #   application index            
              subscriber_address: str       #   address of the subscriber to be granted
              ) -> Tuple[str, DopError]:    #   returns transactionid, DopError
              
            # see 06_pub_call_grant.py
            if self._i_algod_client == None:
                return "",DopError(1,"Missing value for algod client.")

            smart_contract_arguments = {
                    "args":     ['grant']                   #   list of app arguments
                ,   "addrs":    [subscriber_address]        #   list of account arguments
                }

            transaction_note = "DOP GRANT"

            err: DopError
            txid: str = ""
            txid, err = self.dopSmartContract(
                self._i_algod_client
            ,   int(contract_address)
            ,   publisher_passw
            ,   smart_contract_arguments
            ,   transaction_note
            )

            if err.isError():
                return "",err

            try:
                confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  

                #   print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
                #   print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

            except Exception as err:
                #print(err)
                return txid,DopError(306,"An exception occurred while waiting for \
                    confirmation of grant transaction.")

            return txid,DopError(0,"")
            



    def revoke(self,
              publisher_address: str,       #   not used
              publisher_passw: str,         #   publisher private key mnemonic
              contract_address: str,        #   application index            
              subscriber_address: str       #   address of the subscriber to be revoked
              ) -> Tuple[str, DopError]:    #   returns transactionid, DopError

              # see 07_pub_call_revoke.py
            if self._i_algod_client == None:
                return "",DopError(1,"Missing value for algod client.")

            smart_contract_arguments = {
                "args":     ['revoke']                   #   list of app arguments
            ,   "addrs":    [subscriber_address]        #   list of account arguments
            }

            transaction_note = "DOP REVOKE"

            txid: str = ""
            err: DopError
            txid, err = self.dopSmartContract(
                self._i_algod_client
            ,   contract_address
            ,   publisher_passw
            ,   smart_contract_arguments
            ,   transaction_note
            )

            if err.isError():
                return "",err

            try:
                confirmed_txn = self.wait_for_confirmation(self._i_algod_client, txid, 4)  

                #   print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
                #   print("Decoded note: {}".format(base64.b64decode(confirmed_txn["txn"]["txn"]["note"]).decode()))

            except Exception as err:
                #print(err)
                return txid,DopError(307,"An exception occurred while waiting for \
                    confirmation of revoke transaction.")

            return txid,DopError(0,"")



    def balance(self,
                subscriber_address: str,                            #   subscriber EoA address
                secret: str,                                        #   subscriber contract secret
                contract_address: str) -> Tuple[dict, DopError]:       #   address (blockchain layer) of the contract
        """
        Get the balance of a user with `address` of the contract with `contract_address`
        """
        """
        in this version this method is not "really" implemented
        """
        response = {}
        response['subscribed'] = 1
        response['granted'] = 1             #   shortcut - use sub_keyget to valorize this field or use postgres DB
        response['credit'] = 100
        response['debit'] = 0

        return (response, DopError(0,""))

    
    def admin_get_grants(self,
                        publisher_address: str,             #   EoA address of the publisher (contract owner)
                        contract_address: str) -> Tuple[list, DopError]:    #   address (blockchain layer) of the contract
        """
        This method is used by the publisher only in order to retrieve the list 
        of the EoA address of the granted subscribers
        """
        return [], DopError()


    def set_starting_balance(self, 
                            address,
                            amount) -> str: # EoA of the user 
        """
        Sets the starting balance of an EoA
        """
        #self._own_mnemonic = "ability improve suspect canyon castle fire flock forum monitor travel know write similar denial thought \
        #    online ripple squeeze this finish jar parrot rabbit ability crouch"
        if self._own_mnemonic == None:
            return ""

        txid, err = self.__account_send(from_mnemonic = self._own_mnemonic, to_address=address, amount=amount)
        if err.isError():
            return "" 

        return txid



