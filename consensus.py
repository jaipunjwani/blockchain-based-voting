import time
from constants import MINIMUM_AGREEMENT_PCT


class ConsensusParticipant:
    """
    Mixin-style class that is used with Nodes to utilize our consensus algorithm, which is based on
    Ripple Protocol Consensus Algorithm (RPCA). Our algorithm can be summarized as the following:

    For all nodes in network:
        broadcast hash of previous block
        exclude nodes with different hash
  
        broadcast candidate set of transactions
        validate global candidate set of transactions
  
        broadcast transaction approvals
        aggregate approved transactions into new block
    """
    def begin_consensus_round(self, nodes=None):
        """
        Args:
            nodes  nodes to participate in consensus with. used to whitelist nodes
                    when nodes with a different block hash are detected. defaults
                    to entire network
        """
        if nodes:
            try:
                nodes.remove(self)
            except ValueError as e:
                print(e)
        else:
            nodes = self.node_mapping.values()
        self.last_round_nodes = nodes
        self.rejection_map = {}
        self.send_nodes_transactions_for_consensus(nodes)

    def send_nodes_transactions_for_consensus(self, nodes):
        """Sends verified transactions to all nodes in the network specifically for the consensus round"""
        for node in nodes:
            node.check_transactions_for_consensus(self.verified_transactions)

    def check_transactions_for_consensus(self, transactions):
        """Validates a collection of transactions and adjusts each one's tally during the consensus round.
        Args:
            transactions            iterable of Transactions to check
        """
        for tx in transactions:
            # TODO - check this logic...
            if tx in self.transaction_tally:
                self.transaction_tally[tx] = self.transaction_tally[tx] + 1
            else:
                # validate transaction and set tally accordingly
                try:
                    if tx not in self.verified_transactions:
                        self.validate_transaction(tx)
                    self.transaction_tally[tx] = 1
                except Exception as e:
                    self.rejection_map[tx] = str(e)
                    self.transaction_tally[tx] = 0

    def finalize_consensus_round(self):
        """Finalizes block and resets state for next round"""
        self.last_round_approvals.clear()
        self.last_round_rejections.clear()
        self.last_round_rejection_reasons = ''

        # aggregate results
        network_size = len(self.node_mapping.values()) + 1  # add itself
        approved_transactions = []
        rejected_transactions = []
        for tx in self.transaction_tally:
            tally = self.transaction_tally[tx]
            if tally/network_size >= MINIMUM_AGREEMENT_PCT:
                approved_transactions.append(tx)
                self.last_round_approvals.add(tx)
            else:
                rejected_transactions.append(tx)
                self.last_round_rejections.add(tx)
                self.last_round_rejection_reasons = self.rejection_map.values()

        # finalize block
        self.blockchain.add_block(approved_transactions)

        # reset round
        self.transaction_tally = {}
        for tx in approved_transactions:
            try:
                self.verified_transactions.remove(tx)
            except KeyError:
                pass
            try:
                self.rejected_transactions.remove(tx)
            except KeyError:
                pass

    def get_nodes_in_agreement(self):
        """
        Gets all nodes in agreement with this node's perception of the blockchain.
        """
        nodes_in_agreement = []
        nodes = self.node_mapping.values()
        for node in nodes:
            # compare hashes rather than header b/c hash is unique repr that is the same for a given block
            if self.blockchain.current_block.hash == node.blockchain.current_block.hash:
                nodes_in_agreement.append(node)
        return nodes_in_agreement

    @staticmethod
    def demonstrate_consensus(nodes, blockchain_name):
        """
        Utility method to kick off consensus & display meaningful output.
        """
        print()
        print('Kicking off consensus round for {}'.format(blockchain_name))
        # step 1 -- achieve consensus on last block hash (aggregate consensus stats)
        hash_agreement = {}
        for node in nodes:
            h = node.blockchain.current_block.hash  # hash contains previous block header, which is signed by particular node
            if h in hash_agreement:
                hash_agreement[h].append(node)
            else:
                hash_agreement[h] = [node]
        num_hashes = len(hash_agreement.keys())
        majority_hash = None
        majority_nodes_len = 0

        for h in hash_agreement:
            nodes = hash_agreement[h]
            num_nodes = len(nodes)

            if not majority_hash:
                majority_nodes_len = num_nodes
                majority_hash = h

            elif num_nodes > majority_nodes_len:
                majority_nodes_len = num_nodes
                majority_hash = h

        # step 2 -- kick off consensus round only for nodes that agree with the majority
        if majority_hash:
            nodes = hash_agreement[majority_hash]
            for node in nodes:
                node.begin_consensus_round(nodes=nodes.copy())

            for node in nodes:
                node.finalize_consensus_round()

            # compile stats for each node per group
            for node in nodes:
                if not node.is_adversary:
                    # use any good node to display stats since it will have the same stats as the other good nodes
                    good_node = node  
                    break
            node = good_node
            num_nodes = len(nodes)

            print('Consensus among {} nodes'.format(num_nodes))
            print('Transactions approved: {}'.format(len(node.last_round_approvals)))
            rejection_msg = 'Transactions rejected: {}'.format(len(node.rejection_map))
            if len(node.last_round_rejections) > 0:
                rejected_reasons = list(set(node.rejection_map.values()))
                #TODO: message for consensus round summary seems to have state that is unreset (transaction reasons)
                rejection_msg = '{} Reason(s): {}'.format(rejection_msg, rejected_reasons)
            print(rejection_msg)
        time.sleep(2)