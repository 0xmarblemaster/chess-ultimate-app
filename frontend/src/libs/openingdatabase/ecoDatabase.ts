// Import your JSON file (adjust path as needed)
import ecoData from './eco_interpolated.json';
import ecoDataA from './ecoA.json'
import ecoDataB from './ecoB.json'
import ecoDataC from './ecoC.json'
import ecoDataD from './ecoD.json'
import ecoDataE from './ecoE.json'

// Define the structure of your ECO data
interface EcoEntry {
  name: string;
  moves: string;
}

// Type for the entire ECO database
type EcoDatabase = Record<string, EcoEntry>;

/**
 * Check if a given FEN exists in the ECO database
 * @param fen - The FEN string to check
 * @param ecoDatabase - The ECO database object (defaults to imported data)
 * @returns The ECO entry if found, null if not found
 */
export function checkFenInEco(fen: string, ecoDatabase: EcoDatabase): EcoEntry | null {
  return ecoDatabase[fen] || null;
}

/**
 * Check if a FEN exists and return boolean
 * @param fen - The FEN string to check
 * @param ecoDatabase - The ECO database object (defaults to imported data)
 * @returns true if FEN exists, false otherwise
 */
export function fenExists(fen: string, ecoDatabase: EcoDatabase): boolean {
  return fen in ecoDatabase;
}

export function isFenInAllDatabases(fen: string): boolean {
    return fenExists(fen, ecoDataA) || fenExists(fen, ecoDataB) || fenExists(fen, ecoDataC) || fenExists(fen, ecoDataD) || fenExists(fen, ecoDataE) || fenExists(fen, ecoData);
}
