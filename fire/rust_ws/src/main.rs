fn main() {
    println!("Rust MEV Scanner Active");
    loop {
        println!("Scanning blocks...");
        std::thread::sleep(std::time::Duration::from_secs(5));
    }
}
