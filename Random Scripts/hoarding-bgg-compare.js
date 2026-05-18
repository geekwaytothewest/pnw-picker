#!/usr/bin/env node
// hoarding-bgg-compare.js
//
// Looks up BGG playtimes for a list of games and outputs a playtime reference table.
//
// Usage:
//   BGG_TOKEN=your-bearer-token node hoarding-bgg-compare.js games.csv
//
// Requires a BGG application token. Register at https://boardgamegeek.com/applications
//
// Input: CSV exported from "Collection Games Export.sql" (headers: gameId, name)
// gameId should match the gameId column in your Copy/Game tables.
// Output is printed as a table and also written to bgg-playtimes.json.

import fs from 'fs';

const inputFile = process.argv[2];
if (!inputFile) {
    console.error('Usage: node hoarding-bgg-compare.js games.csv');
    process.exit(1);
}

function parseCsv(text) {
    const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim().split('\n');
    const headers = splitCsvRow(lines[0]);
    return lines.slice(1).filter(l => l.trim()).map(line => {
        const values = splitCsvRow(line);
        return Object.fromEntries(headers.map((h, i) => [h.trim(), values[i]?.trim() ?? '']));
    });
}

function splitCsvRow(row) {
    const fields = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < row.length; i++) {
        const ch = row[i];
        if (ch === '"') {
            if (inQuotes && row[i + 1] === '"') { current += '"'; i++; }
            else inQuotes = !inQuotes;
        } else if (ch === ',' && !inQuotes) {
            fields.push(current);
            current = '';
        } else {
            current += ch;
        }
    }
    fields.push(current);
    return fields;
}

const rawGames = parseCsv(fs.readFileSync(inputFile, 'utf8'));
if (!rawGames.length || !('name' in rawGames[0])) {
    console.error('CSV must have headers including "gameId" and "name".');
    process.exit(1);
}
const games = rawGames.map(r => ({ gameId: r.gameId, name: r.name }));

// ---------------------------------------------------------------------------
// BGG API helpers
// ---------------------------------------------------------------------------
const sleep = ms => new Promise(r => setTimeout(r, ms));

const bggToken = process.env.BGG_TOKEN;

async function bggFetch(url, retries = 5) {
    for (let i = 0; i < retries; i++) {
        const res = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${bggToken}`,
            },
        });
        if (res.status === 202) { await sleep(5000); continue; }
        if (res.status === 429) { await sleep(10000); continue; }
        if (!res.ok) {
            const body = await res.text().catch(() => '');
            throw new Error(`BGG ${res.status} for ${url} — ${body.slice(0, 120)}`);
        }
        return res.text();
    }
    throw new Error('BGG kept returning 202/429 after retries');
}

async function searchBGG(name) {
    // Exact match first
    const xml = await bggFetch(
        `https://boardgamegeek.com/xmlapi2/search?query=${encodeURIComponent(name)}&type=boardgame&exact=1`
    );
    const exact = xml.match(/item type="boardgame" id="(\d+)"/);
    if (exact) return exact[1];

    await sleep(2000);

    // Fuzzy fallback — take first result
    const xml2 = await bggFetch(
        `https://boardgamegeek.com/xmlapi2/search?query=${encodeURIComponent(name)}&type=boardgame`
    );
    const fuzzy = xml2.match(/item type="boardgame" id="(\d+)"/);
    return fuzzy ? fuzzy[1] : null;
}

async function getPlaytime(bggId) {
    const xml = await bggFetch(`https://boardgamegeek.com/xmlapi2/thing?id=${bggId}`);
    const minMatch = xml.match(/<minplaytime value="(\d+)"/);
    const maxMatch = xml.match(/<maxplaytime value="(\d+)"/);
    return {
        bggId,
        min: minMatch ? parseInt(minMatch[1], 10) : null,
        max: maxMatch ? parseInt(maxMatch[1], 10) : null,
    };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
    if (!bggToken) {
        console.error('BGG_TOKEN is required. Register an application at https://boardgamegeek.com/applications to get a Bearer token.');
        console.error('  BGG_TOKEN=your-token node hoarding-bgg-compare.js games.csv');
        process.exit(1);
    }

    console.log(`Looking up ${games.length} games on BGG...\n`);

    const results = [];

    for (const game of games) {
        process.stdout.write(`  ${game.name} ... `);
        try {
            const bggId = await searchBGG(game.name);
            await sleep(2000);
            if (!bggId) {
                console.log('not found');
                results.push({ gameId: game.gameId, name: game.name, bggId: null, minTime: null, maxTime: null });
                continue;
            }
            const playtime = await getPlaytime(bggId);
            await sleep(2000);
            console.log(playtime.min != null ? `${playtime.min}–${playtime.max} min` : 'no playtime data');
            results.push({ gameId: game.gameId, name: game.name, bggId: playtime.bggId, minTime: playtime.min, maxTime: playtime.max });
        } catch (err) {
            console.log(`error: ${err.message}`);
            results.push({ gameId: game.gameId, name: game.name, bggId: null, minTime: null, maxTime: null });
        }
    }

    // Print table
    console.log('\n' + '='.repeat(72));
    console.log('gameId  minTime  maxTime  name');
    console.log('='.repeat(72));
    for (const r of results) {
        const min = r.minTime != null ? String(r.minTime).padStart(7) : '    N/A';
        const max = r.maxTime != null ? String(r.maxTime).padStart(7) : '    N/A';
        console.log(`${String(r.gameId).padStart(6)}  ${min}  ${max}  ${r.name}`);
    }

    // Write JSON output for use in further analysis
    const outFile = 'bgg-playtimes.json';
    fs.writeFileSync(outFile, JSON.stringify(results, null, 2));
    console.log(`\nWritten to ${outFile}`);
}

main().catch(err => { console.error(err); process.exit(1); });
