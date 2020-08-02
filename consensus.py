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
                pass
        else:
            nodes = self.node_mapping.values()
        self.last_round_nodes = nodes  # future work: will help detect difference in nodes between previous round
        self.rejection_map = {}
        self.broadcast_transactions_for_consensus(nodes)

    def broadcast_transactions_for_consensus(self, nodes):
        """Broadcasts verified transactions to all nodes in the network specifically for the consensus round"""
        for node in nodes:
            node.validate_transactions_for_consensus(self.verified_transactions)

    def validate_transactions_for_consensus(self, transactions):
        """
        Validates a collection of transactions and votes on the validity of each during the consensus round.
        Args:
            transactions            iterable of Transactions to check
        """
        for tx in transactions:
            # validate transaction if not already done so and set tally accordingly
            try:
                if tx not in self.verified_transactions:
                    self.validate_transaction(tx)
                self.transaction_tally[tx] = 1
            except Exception as e:
                self.rejection_map[tx] = str(e)
                self.transaction_tally[tx] = 0

    def broadcast_transaction_tally(self, nodes):
        """Broadcasts nodes tally on all transactions during consensus round."""
        for node in nodes:
            node.aggregate_transaction_tally(self.transaction_tally)

    def aggregate_transaction_tally(self, transaction_tally):
        """Increment transaction tally from another node for known transactions from consensus round."""
        for tx in self.transaction_tally:
            self.transaction_tally[tx] += transaction_tally.get(tx, 0)

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

    @staticmethod
    def demonstrate_consensus(nodes, blockchain_name):
        """
        Utility method to kick off consensus & display meaningful output.
        """
        print()
        print('Kicking off consensus round for {}'.format(blockchain_name))

        peer_map = {}  # node: nodes in agreement

        for node in nodes:
            # step 1 -- determine which nodes are in agreement of state
            peers = node.get_nodes_in_agreement()
            peer_map[node] = peers

            # step 2 -- send transactions to peers for validation
            node.begin_consensus_round(nodes=peers)

        for node in nodes:
            # step 3 -- broadcast tally for all transactions
            node.broadcast_transaction_tally(nodes=peer_map[node])

        for node in nodes: 
            # step 4 -- commit block of valid transactions
            node.finalize_consensus_round()

        # extract stats from any good node, which will have the same block as any other good node
        for node in nodes:
            if not node.is_adversary:
                good_node = node  
                break
        node = good_node
        num_nodes = len(node.get_nodes_in_agreement())

        print('Consensus among {} nodes'.format(num_nodes))
        print('Transactions approved: {}'.format(len(node.last_round_approvals)))
        rejection_msg = 'Transactions rejected: {}'.format(len(node.rejection_map))
        if len(node.last_round_rejections) > 0:
            rejected_reasons = list(set(node.rejection_map.values()))
            rejection_msg = '{} Reason(s): {}'.format(rejection_msg, rejected_reasons)
        print(rejection_msg)
        time.sleep(2)