import time
from constants import MINIMUM_AGREEMENT_PCT


class ConsensusParticipant:
    """
    Mixin-style class that is used with Nodes to utilize our consensus algorithm, which is inspired by
    parts of Practical Byzantine Fault Tolerance (PBFT) and the Ripple Protocol Consensus Algorithm (RPCA). 
    Our algorithm can be summarized as the following:

    For all nodes in network:
        broadcast hash of previous block
        exclude nodes with different hash
  
        broadcast candidate set of transactions
        validate global candidate set of transactions
  
        broadcast transaction approvals
        aggregate approved transactions into new block
    """

    def __init__(self):
        self.transaction_tally = dict()  # holds tally for each transaction during consensus round
        self.last_round_approvals = set()
        self.last_round_rejections = set()
        self.transaction_rejection_reasons = {}  # tx: 'error msg'

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
        self.transaction_rejection_reasons = {}
        self.broadcast_transactions_for_consensus(nodes)

    def broadcast_transactions_for_consensus(self, nodes):
        """Broadcasts verified transactions to all nodes in the network specifically for the consensus round"""
        for node in nodes:
            node.validate_transactions_for_consensus(self.verified_transactions)

    def validate_transactions_for_consensus(self, transactions):
        """
        Validates a collection of transactions and votes on the validity of each during the consensus round.
        Resolves conflicting transactions by accepting one with earlier timestamp.
        Args:
            transactions            iterable of Transactions to check
        """
        transaction_reprs = {}
        for tx in transactions:
            # validate transaction if not already done so and set tally accordingly
            try:
                if tx not in self.verified_transactions:
                    self.validate_transaction(tx)

                # transaction is valid on its own. Now compare to other transactions and find conflicting ones.
                # resolve conflict by accepting transaction with earlier timestamp
                tx_repr = tx.get_unique_repr()
                if tx_repr in transaction_reprs:
                    conflicting_tx = transaction_reprs[tx_repr]
                    if tx.time > conflicting_tx.time:
                        raise Exception('Conflicting transaction with earlier timestamp found.')
                else:
                    transaction_reprs[tx_repr] = tx

                self.transaction_tally[tx] = 1
            except Exception as e:
                self.transaction_rejection_reasons[tx] = str(e)
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

        # aggregate results
        network_size = len(self.node_mapping.values()) + 1  # add itself
        for tx in self.transaction_tally:
            tally = self.transaction_tally[tx]
            if tally/network_size >= MINIMUM_AGREEMENT_PCT:
                self.last_round_approvals.add(tx)
            else:
                self.last_round_rejections.add(tx)

        # finalize block
        self.blockchain.add_block(list(self.last_round_approvals))

        # reset round
        self.transaction_tally = {}
        for tx in self.last_round_approvals:
            if tx in self.verified_transactions:
                self.verified_transactions.remove(tx)
            if tx in self.rejected_transactions:
                self.rejected_transactions.remove(tx)

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

        # extract stats from any good node, which will have the same state due to the same behavior as any other good node
        for node in nodes:
            if not node.is_adversary:
                good_node = node  
                break
        node = good_node
        num_nodes = len(node.get_nodes_in_agreement()) + 1  # peers + self

        print('Consensus among {} nodes'.format(num_nodes))
        print('Transactions approved: {}'.format(len(node.last_round_approvals)))
        rejection_msg = 'Transactions rejected: {}'.format(len(node.transaction_rejection_reasons))
        if len(node.last_round_rejections) > 0:
            rejected_reasons = list(set(node.transaction_rejection_reasons.values()))
            rejection_msg = '{} Reason(s): {}'.format(rejection_msg, rejected_reasons)
        print(rejection_msg)
        time.sleep(2)