#!/usr/bin/env node
/**
 * Casper transaction runner — executes write operations via casper-js-sdk.
 * Usage: node tx_runner.mjs <operation> '<json-params>'
 */

import {
  Deploy,
  DeployHeader,
  ExecutableDeployItem,
  TransferDeployItem,
  StoredContractByHash,
  Args,
  CLValue,
  PrivateKey,
  PublicKey,
  KeyAlgorithm,
  Timestamp,
  Duration,
  Hash,
} from 'casper-js-sdk';
import { ethers } from 'ethers';
import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const rpcUrl = (process.env.CASPER_NODE_URL || process.env.CASPER_RPC_URL || 'https://node.testnet.casper.network/rpc').replace(/\/$/, '');
const apiKey = process.env.CASPER_API_KEY;
const chainName = process.env.CASPER_CHAIN_NAME || 'casper-test';
const signingHex = process.env.CASPER_SIGNING_KEY_HEX || process.env.CASPER_PRIVATE_KEY;
const signingPem = process.env.CASPER_SIGNING_KEY_PEM;
const DEFAULT_TTL = 1800000;
const DEFAULT_GAS = '2500000000';

function fail(msg) {
  console.log(JSON.stringify({ error: msg }));
  process.exit(1);
}

function ok(data) {
  console.log(JSON.stringify(data));
  process.exit(0);
}

function getSigningKey() {
  const algo = KeyAlgorithm.ED25519;
  if (signingPem) return PrivateKey.fromPem(signingPem, algo);
  if (signingHex) return PrivateKey.fromHex(signingHex.replace(/^0x/, ''), algo);
  fail('No signing key. Set CASPER_SIGNING_KEY_HEX or CASPER_SIGNING_KEY_PEM');
}

async function submitDeploy(deploy) {
  const deployJson = Deploy.toJSON(deploy);
  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers.Authorization = apiKey;
  const response = await axios.post(
    rpcUrl.endsWith('/rpc') ? rpcUrl : `${rpcUrl}/rpc`,
    { jsonrpc: '2.0', method: 'account_put_deploy', params: { deploy: deployJson }, id: 1 },
    { timeout: 30000, headers }
  );
  if (response.data.error) fail(response.data.error.message || JSON.stringify(response.data.error));
  return response.data.result.deploy_hash;
}

async function signAndSubmit(session, gasPayment = DEFAULT_GAS) {
  const signingKey = getSigningKey();
  const header = new DeployHeader(chainName, [], 1, new Timestamp(new Date()), new Duration(DEFAULT_TTL), signingKey.publicKey);
  const payment = ExecutableDeployItem.standardPayment(gasPayment);
  const deploy = Deploy.makeDeploy(header, payment, session);
  deploy.sign(signingKey);
  const deployHash = await submitDeploy(deploy);
  return { deploy_hash: deployHash, chain_name: chainName, explorer_url: `https://testnet.cspr.live/deploy/${deployHash}` };
}

async function callContract(contractHash, entryPoint, argsMap = {}, gasPayment = DEFAULT_GAS) {
  const clean = contractHash.replace(/^hash-/, '').replace(/^0x/, '');
  const hashBytes = ethers.getBytes(clean.length === 64 ? clean : clean);
  const contractHashObj = new Hash(hashBytes);
  const runtimeArgs = argsMap instanceof Args ? argsMap : new Args(argsMap);
  const storedContract = new StoredContractByHash(contractHashObj, entryPoint, runtimeArgs);
  const session = new ExecutableDeployItem();
  session.storedContractByHash = storedContract;
  return signAndSubmit(session, gasPayment);
}

function pubKey(hex) {
  return PublicKey.fromHex(hex.replace(/^0x/, ''), KeyAlgorithm.ED25519);
}

function amountUnits(amount, decimals = 9) {
  return ethers.parseUnits(String(amount), decimals).toString();
}

const OPS = {
  async transfer(p) {
    const target = pubKey(p.to_public_key);
    const amountMotes = amountUnits(p.amount_cspr, 9);
    const transferItem = TransferDeployItem.newTransfer(amountMotes, target, null, p.transfer_id ?? Math.floor(Math.random() * 1e6));
    const session = new ExecutableDeployItem();
    session.transfer = transferItem;
    return signAndSubmit(session, p.gas_payment || DEFAULT_GAS);
  },

  async call_contract(p) {
    const args = new Args(new Map());
    for (const [k, v] of Object.entries(p.args || {})) {
      if (typeof v === 'number') args.insert(k, CLValue.newCLUInt64(v));
      else if (typeof v === 'boolean') args.insert(k, CLValue.newCLBool(v));
      else args.insert(k, CLValue.newCLString(String(v)));
    }
    return callContract(p.contract_hash, p.entry_point, args, p.gas_payment || DEFAULT_GAS);
  },

  async cep18_mint(p) {
    return callContract(p.contract_hash, 'mint', Args.fromMap({
      owner: CLValue.newCLPublicKey(pubKey(p.owner)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_burn(p) {
    return callContract(p.contract_hash, 'burn', Args.fromMap({
      owner: CLValue.newCLPublicKey(pubKey(p.owner)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_transfer(p) {
    return callContract(p.contract_hash, 'transfer', Args.fromMap({
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_approve(p) {
    return callContract(p.contract_hash, 'approve', Args.fromMap({
      spender: CLValue.newCLPublicKey(pubKey(p.spender)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_increase_allowance(p) {
    return callContract(p.contract_hash, 'increase_allowance', Args.fromMap({
      spender: CLValue.newCLPublicKey(pubKey(p.spender)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_decrease_allowance(p) {
    return callContract(p.contract_hash, 'decrease_allowance', Args.fromMap({
      spender: CLValue.newCLPublicKey(pubKey(p.spender)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async cep18_transfer_from(p) {
    return callContract(p.contract_hash, 'transfer_from', Args.fromMap({
      owner: CLValue.newCLPublicKey(pubKey(p.owner)),
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },

  async cep47_mint(p) {
    const args = Args.fromMap({
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      token_id: CLValue.newCLString(String(p.token_id)),
    });
    return callContract(p.contract_hash, 'mint', args);
  },
  async cep47_mint_copies(p) {
    return callContract(p.contract_hash, 'mint_copies', Args.fromMap({
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      count: CLValue.newCLUint64(Number(p.count)),
    }));
  },
  async cep47_burn(p) {
    return callContract(p.contract_hash, 'burn', Args.fromMap({ token_id: CLValue.newCLString(String(p.token_id)) }));
  },
  async cep47_transfer(p) {
    return callContract(p.contract_hash, 'transfer', Args.fromMap({
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      token_id: CLValue.newCLString(String(p.token_id)),
    }));
  },
  async cep47_approve(p) {
    return callContract(p.contract_hash, 'approve', Args.fromMap({
      spender: CLValue.newCLPublicKey(pubKey(p.spender)),
      token_id: CLValue.newCLString(String(p.token_id)),
    }));
  },
  async cep47_transfer_from(p) {
    return callContract(p.contract_hash, 'transfer_from', Args.fromMap({
      owner: CLValue.newCLPublicKey(pubKey(p.owner)),
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      token_id: CLValue.newCLString(String(p.token_id)),
    }));
  },

  async cep78_set_metadata(p) {
    return callContract(p.contract_hash, 'set_token_metadata', Args.fromMap({
      token_id: CLValue.newCLString(String(p.token_id)),
      metadata: CLValue.newCLString(String(p.metadata)),
    }));
  },
  async cep78_batch_transfer(p) {
    return callContract(p.contract_hash, 'batch_transfer', Args.fromMap({
      recipient: CLValue.newCLPublicKey(pubKey(p.recipient)),
      token_ids: CLValue.newCLString((p.token_ids || []).join(',')),
    }));
  },
  async cep78_batch_burn(p) {
    return callContract(p.contract_hash, 'batch_burn', Args.fromMap({
      token_ids: CLValue.newCLString((p.token_ids || []).join(',')),
    }));
  },
  async cep78_set_admin(p) {
    return callContract(p.contract_hash, 'set_admin', Args.fromMap({
      admin: CLValue.newCLPublicKey(pubKey(p.admin)),
    }));
  },

  async bond(p) {
    const args = Args.fromMap({ amount: CLValue.newCLUInt512(amountUnits(p.amount_cspr, 9)) });
    if (p.delegator_rate !== undefined) args.insert('delegator_rate', CLValue.newCLUint8(Number(p.delegator_rate)));
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), args));
  },
  async delegate(p) {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      validator: CLValue.newCLPublicKey(pubKey(p.validator)),
      amount: CLValue.newCLUInt512(amountUnits(p.amount_cspr, 9)),
    })));
  },
  async unbond(p) {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      amount: CLValue.newCLUInt512(amountUnits(p.amount_cspr, 9)),
    })));
  },
  async undelegate(p) {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      validator: CLValue.newCLPublicKey(pubKey(p.validator)),
      amount: CLValue.newCLUInt512(amountUnits(p.amount_cspr, 9)),
    })));
  },
  async withdraw_rewards() {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), new Args(new Map())));
  },
  async set_commission_rate(p) {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      commission_rate: CLValue.newCLUint8(Number(p.commission_rate)),
    })));
  },

  async amm_swap(p) {
    return callContract(p.contract_hash, 'swap', Args.fromMap({
      token_in: CLValue.newCLByteArray(ethers.getBytes(p.token_in.replace(/^0x/, ''))),
      token_out: CLValue.newCLByteArray(ethers.getBytes(p.token_out.replace(/^0x/, ''))),
      amount_in: CLValue.newCLUInt256(amountUnits(p.amount_in, p.decimals ?? 9)),
      min_amount_out: CLValue.newCLUInt256(amountUnits(p.min_amount_out, p.decimals ?? 9)),
    }));
  },
  async add_liquidity(p) {
    return callContract(p.contract_hash, 'add_liquidity', Args.fromMap({
      token_a: CLValue.newCLByteArray(ethers.getBytes(p.token_a.replace(/^0x/, ''))),
      token_b: CLValue.newCLByteArray(ethers.getBytes(p.token_b.replace(/^0x/, ''))),
      amount_a: CLValue.newCLUInt256(amountUnits(p.amount_a, p.decimals ?? 9)),
      amount_b: CLValue.newCLUInt256(amountUnits(p.amount_b, p.decimals ?? 9)),
    }));
  },
  async remove_liquidity(p) {
    return callContract(p.contract_hash, 'remove_liquidity', Args.fromMap({
      lp_token: CLValue.newCLByteArray(ethers.getBytes(p.lp_token.replace(/^0x/, ''))),
      lp_amount: CLValue.newCLUInt256(amountUnits(p.lp_amount, p.decimals ?? 9)),
      min_amount_a: CLValue.newCLUInt256(amountUnits(p.min_amount_a, p.decimals ?? 9)),
      min_amount_b: CLValue.newCLUInt256(amountUnits(p.min_amount_b, p.decimals ?? 9)),
    }));
  },
  async stake_lp(p) {
    return callContract(p.contract_hash, 'stake_lp', Args.fromMap({
      lp_token: CLValue.newCLByteArray(ethers.getBytes(p.lp_token.replace(/^0x/, ''))),
      amount: CLValue.newCLUInt256(amountUnits(p.amount, p.decimals ?? 9)),
    }));
  },
  async claim_reward(p) {
    return callContract(p.contract_hash, 'claim_reward', new Args(new Map()));
  },
  async create_order(p) {
    return callContract(p.contract_hash, 'create_order', Args.fromMap({
      token_in: CLValue.newCLByteArray(ethers.getBytes(p.token_in.replace(/^0x/, ''))),
      token_out: CLValue.newCLByteArray(ethers.getBytes(p.token_out.replace(/^0x/, ''))),
      amount_in: CLValue.newCLUInt256(amountUnits(p.amount_in, p.decimals ?? 9)),
      price: CLValue.newCLUInt256(amountUnits(p.price, p.decimals ?? 9)),
    }));
  },
  async cancel_order(p) {
    return callContract(p.contract_hash, 'cancel_order', Args.fromMap({
      order_id: CLValue.newCLString(String(p.order_id)),
    }));
  },

  async counter_increment(p) {
    return callContract(p.contract_hash, 'counter_inc', new Args(new Map()));
  },
  async counter_decrement(p) {
    return callContract(p.contract_hash, 'counter_dec', new Args(new Map()));
  },
  async dictionary_put(p) {
    return callContract(p.contract_hash, 'dictionary_put', Args.fromMap({
      key: CLValue.newCLString(String(p.key)),
      value: CLValue.newCLString(String(p.value)),
    }));
  },
  async dictionary_remove(p) {
    return callContract(p.contract_hash, 'dictionary_remove', Args.fromMap({
      key: CLValue.newCLString(String(p.key)),
    }));
  },
  async create_proposal(p) {
    return callContract(p.contract_hash, 'create_proposal', Args.fromMap({
      title: CLValue.newCLString(String(p.title)),
      description: CLValue.newCLString(String(p.description)),
      voting_duration: CLValue.newCLUint64(Number(p.voting_duration)),
    }));
  },
  async cast_vote(p) {
    const voteByte = String(p.vote_option || '').toLowerCase().startsWith('for') ? 1 : 0;
    return callContract(p.contract_hash, 'cast_vote', Args.fromMap({
      proposal_id: CLValue.newCLString(String(p.proposal_id)),
      vote: CLValue.newCLUint8(voteByte),
    }));
  },
  async execute_proposal(p) {
    return callContract(p.contract_hash, 'execute_proposal', Args.fromMap({
      proposal_id: CLValue.newCLString(String(p.proposal_id)),
    }));
  },
  async save_asset_record(p) {
    const args = Args.fromMap({
      asset_id: CLValue.newCLString(String(p.asset_id)),
      owner_hash: CLValue.newCLByteArray(ethers.getBytes(p.owner_hash.replace(/^0x/, ''))),
      document_hash: CLValue.newCLByteArray(ethers.getBytes(p.document_hash.replace(/^0x/, ''))),
    });
    if (p.metadata) args.insert('metadata', CLValue.newCLString(String(p.metadata)));
    return callContract(p.contract_hash, 'save_asset_record', args);
  },

  async create_purse(p) {
    const args = new Args(new Map());
    if (p.purse_name) args.insert('purse_name', CLValue.newCLString(String(p.purse_name)));
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), args));
  },
  async add_associated_key(p) {
    const pk = pubKey(p.public_key);
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      key: CLValue.newCLByteArray(pk.accountHash().toBytes()),
      weight: CLValue.newCLUint8(Number(p.weight)),
    })));
  },
  async remove_associated_key(p) {
    const pk = pubKey(p.public_key);
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      key: CLValue.newCLByteArray(pk.accountHash().toBytes()),
    })));
  },
  async set_action_threshold(p) {
    const actionType = String(p.action_type || 'deployment').toLowerCase() === 'key_management' ? 1 : 0;
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      action_type: CLValue.newCLUint8(actionType),
      threshold: CLValue.newCLUint8(Number(p.threshold)),
    })));
  },
  async put_named_key(p) {
    return signAndSubmit(ExecutableDeployItem.newModuleBytes(new Uint8Array(0), Args.fromMap({
      name: CLValue.newCLString(String(p.name)),
      key: CLValue.newCLKey(new Hash(ethers.getBytes(p.key_value.replace(/^0x/, '')))),
    })));
  },
};

async function main() {
  const op = process.argv[2];
  const paramsRaw = process.argv[3] || '{}';
  if (!op || !OPS[op]) fail(`Unknown operation: ${op}. Available: ${Object.keys(OPS).join(', ')}`);
  let params;
  try {
    params = JSON.parse(paramsRaw);
  } catch {
    fail('Invalid JSON params');
  }
  try {
    ok(await OPS[op](params));
  } catch (e) {
    fail(e.message || String(e));
  }
}

main();
