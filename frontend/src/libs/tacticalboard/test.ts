import { Board } from "./board";

const b = new Board("2r2rk1/1p1q1p1p/pN2p1p1/3pPn2/3P1Q2/7P/PP3PP1/2R2RK1 b - - 7 17");
console.log(b.toString());

const b2 = new Board("2r2rk1/1p1q1p2/pN2p1pp/3pPn2/3P1Q2/7P/PP3PP1/2R2RK1 w - - 0 18");
console.log(b2.toString());

const b3 = new Board("3r1rk1/1p1q1p2/pN2p1pp/3pPn2/3P4/7P/PP1Q1PP1/2R2RK1 w - - 2 19");
console.log(b3.toString());

const b4 = new Board("5k2/5R2/4p1Kp/3p2p1/2nP4/2P4P/5n2/8 b - - 3 50");
console.log(b4.toString());

const b5 = new Board("r2qkbnr/ppp2ppp/2np4/1B2p3/4P1b1/5N2/PPPP1PPP/RNBQ1RK1 w kq - 2 5");
console.log(b5.toString());

const b6 = new Board("r3kbnr/2pq1ppp/p1Bp4/8/4P3/8/PPP2PPP/RNBR2K1 w kq - 1 10");
console.log(b6.toString())