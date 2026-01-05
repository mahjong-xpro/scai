use crate::tile::{Tile, Wall};
use crate::game::state::GameState;
use crate::game::action::Action;
use crate::game::pong::PongHandler;
use crate::game::kong::KongHandler;
use crate::game::blood_battle::BloodBattleRules;
use crate::tile::win_check::WinChecker;
use crate::game::settlement::GangSettlement;

/// 游戏引擎错误
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameError {
    /// 无效的玩家 ID
    InvalidPlayer,
    /// 无效的动作
    InvalidAction,
    /// 游戏已结束
    GameOver,
    /// 玩家已离场
    PlayerOut,
}

/// 游戏结果
#[derive(Debug, Clone)]
pub struct GameResult {
    /// 最终结算结果
    pub final_settlement: FinalSettlementResult,
}

/// 最终结算结果
#[derive(Debug, Clone)]
pub struct FinalSettlementResult {
    /// 所有结算结果（查大叫、查花猪、退税等）
    pub settlements: Vec<crate::game::settlement::SettlementResult>,
}

/// 游戏引擎
/// 
/// 负责管理游戏流程和动作处理
#[derive(Clone)]
pub struct GameEngine {
    /// 游戏状态
    pub state: GameState,
    /// 牌墙
    pub wall: Wall,
}

impl GameEngine {
    /// 创建新的游戏引擎
    pub fn new() -> Self {
        let mut wall = Wall::new();
        wall.shuffle();
        
        Self {
            state: GameState::new(),
            wall,
        }
    }

    /// 初始化游戏（发牌）
    pub fn initialize(&mut self) -> Result<(), GameError> {
        // 发牌给 4 个玩家（每人 13 张）
        for i in 0..4 {
            for _ in 0..13 {
                if let Some(tile) = self.wall.draw() {
                    self.state.players[i].hand.add_tile(tile);
                } else {
                    return Err(GameError::GameOver);
                }
            }
        }
        Ok(())
    }

    /// 处理动作
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 执行动作的玩家 ID
    /// - `action`: 动作
    /// 
    /// # 返回
    /// 
    /// 动作处理结果
    pub fn process_action(&mut self, player_id: u8, action: Action) -> Result<ActionResult, GameError> {
        if player_id >= 4 {
            return Err(GameError::InvalidPlayer);
        }

        if self.state.players[player_id as usize].is_out {
            return Err(GameError::PlayerOut);
        }

        match action {
            Action::Draw => self.handle_draw(player_id),
            Action::Discard { tile } => self.handle_discard(player_id, tile),
            Action::Pong { tile } => self.handle_pong(player_id, tile),
            Action::Gang { tile, is_concealed } => self.handle_gang(player_id, tile, is_concealed),
            Action::Win => self.handle_win(player_id),
            Action::Pass => {
                // 处理过胡：如果上一个动作是出牌，且当前玩家可以胡，则记录过胡番数
                if let Some(Action::Discard { tile }) = self.state.last_action {
                    let player = &self.state.players[player_id as usize];
                    
                    // 检查是否可以胡这张牌
                    let mut test_hand = player.hand.clone();
                    test_hand.add_tile(tile);
                    let mut checker = WinChecker::new();
                    let melds_count = player.melds.len() as u8;
                    let win_result = checker.check_win_with_melds(&test_hand, melds_count);
                    
                    if win_result.is_win {
                        // 计算番数
                        use crate::game::scoring::BaseFansCalculator;
                        let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
                        
                        // 记录过胡番数
                        let player = &mut self.state.players[player_id as usize];
                        player.record_passed_win(base_fans);
                    }
                }
                Ok(ActionResult::Passed)
            },
            Action::DeclareSuit { .. } => {
                // 定缺动作应该在 run() 方法的定缺阶段处理，不应该在这里
                Err(GameError::InvalidAction)
            }
        }
    }

    /// 处理摸牌
    fn handle_draw(&mut self, player_id: u8) -> Result<ActionResult, GameError> {
        // 检查是否是最后一张牌
        if self.wall.remaining_count() <= 1 {
            self.state.is_last_tile = true;
        }
        
        if let Some(tile) = self.wall.draw() {
            let player = &mut self.state.players[player_id as usize];
            player.hand.add_tile(tile);
            // 清除过胡锁定（规则：过胡锁定只在"下一次摸牌前"有效）
            player.clear_passed_win();
            
            self.state.last_action = Some(Action::Draw);
            
            // 检查是否是最后一张牌
            if self.wall.remaining_count() == 0 {
                self.state.is_last_tile = true;
            }
            
            Ok(ActionResult::Drawn { tile })
        } else {
            Err(GameError::GameOver)
        }
    }

    /// 处理出牌
    fn handle_discard(&mut self, player_id: u8, tile: Tile) -> Result<ActionResult, GameError> {
        let player = &mut self.state.players[player_id as usize];
        
        // 检查是否可以出这张牌
        if !player.hand.remove_tile(tile) {
            return Err(GameError::InvalidAction);
        }
        
        self.state.last_action = Some(Action::Discard { tile });
        
        // 记录弃牌历史
        self.state.discard_history.push(crate::game::state::DiscardRecord {
            player_id,
            tile,
            turn: self.state.turn,
        });
        
        // 处理出牌后的响应（按优先级）
        match self.handle_discard_responses(player_id, tile)? {
            Some(response_result) => {
                // 有响应，返回响应结果
                Ok(response_result)
            }
            None => {
                // 没有响应，出牌成功，切换到下一个玩家
                self.next_turn()?;
                Ok(ActionResult::Discarded { tile, responses: Vec::new() })
            }
        }
    }

    /// 处理碰牌
    fn handle_pong(&mut self, player_id: u8, tile: Tile) -> Result<ActionResult, GameError> {
        // 检查上一个动作是否是出牌
        let discarded_tile = match self.state.last_action {
            Some(Action::Discard { tile }) => tile,
            _ => return Err(GameError::InvalidAction),
        };
        
        if discarded_tile != tile {
            return Err(GameError::InvalidAction);
        }
        
        // 执行碰牌
        if !PongHandler::pong(&mut self.state.players[player_id as usize], tile) {
            return Err(GameError::InvalidAction);
        }
        
        self.state.last_action = Some(Action::Pong { tile });
        self.state.current_player = player_id;
        
        Ok(ActionResult::Ponged { tile })
    }

    /// 处理杠牌
    fn handle_gang(&mut self, player_id: u8, tile: Tile, is_concealed: bool) -> Result<ActionResult, GameError> {
        let player = &mut self.state.players[player_id as usize];
        
        let kong_type = if is_concealed {
            // 暗杠
            if KongHandler::can_concealed_kong(player, &tile).is_none() {
                return Err(GameError::InvalidAction);
            }
            if !KongHandler::concealed_kong(player, tile) {
                return Err(GameError::InvalidAction);
            }
            crate::game::kong::KongType::Concealed
        } else {
            // 检查是加杠还是直杠
            if let Some(_) = KongHandler::can_add_kong(player, &tile) {
                // 加杠：需要先检查抢杠胡
                return self.handle_add_kong(player_id, tile);
            } else if let Some(_) = KongHandler::can_direct_kong(player, &tile) {
                // 直杠
                if !KongHandler::direct_kong(player, tile) {
                    return Err(GameError::InvalidAction);
                }
                crate::game::kong::KongType::Direct
            } else {
                return Err(GameError::InvalidAction);
            }
        };
        
        // 记录杠牌历史
        self.state.gang_history.push(crate::game::state::GangRecord {
            player_id,
            tile,
            is_concealed,
            turn: self.state.turn,
        });
        
        // 计算杠钱结算（先释放 player 的借用）
        let players = {
            // 限制 player 的借用作用域
            let _ = &player;
            self.state.players.clone()
        };
        let settlement = GangSettlement::calculate_gang_payment(player_id, is_concealed, &players);
        
        // 更新玩家杠钱收入
        let income = settlement.payments.get(&player_id).copied().unwrap_or(0);
        if income > 0 {
            self.state.players[player_id as usize].add_gang_earnings(income);
        }
        
        self.state.last_action = Some(Action::Gang { tile, is_concealed });
        self.state.current_player = player_id;
        
        // 杠后补牌
        if let Some(new_tile) = self.wall.draw() {
            self.state.players[player_id as usize].hand.add_tile(new_tile);
        }
        
        Ok(ActionResult::Ganged { tile, kong_type, settlement })
    }

    /// 运行一局完整的游戏
    /// 
    /// # 参数
    /// 
    /// - `action_callback`: 动作回调函数，根据游戏状态返回玩家动作
    /// 
    /// # 返回
    /// 
    /// 游戏结果
    pub fn run<F>(&mut self, mut action_callback: F) -> Result<GameResult, GameError>
    where
        F: FnMut(&GameState, u8) -> Action,
    {
        // 1. 初始化游戏（发牌）
        self.initialize()?;
        
        // 2. 定缺阶段（所有玩家必须定缺）
        for i in 0..4u8 {
            // 检查是否已经定缺
            if self.state.players[i as usize].declared_suit.is_some() {
                continue;
            }
            
            // 获取玩家定缺选择
            let action = action_callback(&self.state, i);
            if let Action::DeclareSuit { suit } = action {
                // 执行定缺
                if !BloodBattleRules::declare_suit(i, suit, &mut self.state) {
                    return Err(GameError::InvalidAction);
                }
            } else {
                // 如果不是定缺动作，返回错误
                return Err(GameError::InvalidAction);
            }
        }
        
        // 验证所有玩家都已定缺
        if !BloodBattleRules::all_players_declared(&self.state) {
            return Err(GameError::InvalidAction);
        }
        
        // 3. 游戏主循环
        while !self.state.is_game_over() {
            let current_player = self.state.current_player;
            
            // 当前玩家摸牌
            self.handle_draw(current_player)?;
            
            // 获取玩家动作
            let action = action_callback(&self.state, current_player);
            
            // 处理动作
            match self.process_action(current_player, action)? {
                ActionResult::Won { can_continue, .. } => {
                    if !can_continue {
                        break;
                    }
                    // 继续游戏，切换到下一个玩家
                    self.next_turn()?;
                }
                ActionResult::Ponged { .. } | ActionResult::Ganged { .. } => {
                    // 碰或杠后，当前玩家继续出牌
                    // 不需要切换玩家
                }
                ActionResult::Discarded { .. } => {
                    // 出牌后，响应已在 handle_discard 中处理
                    // 如果没有响应，已切换到下一个玩家
                }
                _ => {
                    // 其他情况，切换到下一个玩家
                    self.next_turn()?;
                }
            }
        }
        
        // 4. 游戏结束后的完整结算
        let final_settlement = self.final_settlement();
        
        Ok(GameResult {
            final_settlement,
        })
    }

    /// 处理胡牌（自摸或点炮胡）
    fn handle_win(&mut self, player_id: u8) -> Result<ActionResult, GameError> {
        self.handle_win_internal(player_id, None)
    }

    /// 处理点炮胡
    /// 
    /// # 参数
    /// 
    /// - `winner_id`: 胡牌玩家 ID
    /// - `discarder_id`: 点炮者 ID
    /// - `tile`: 被胡的牌
    fn handle_discard_win(
        &mut self,
        winner_id: u8,
        discarder_id: u8,
        tile: Tile,
    ) -> Result<ActionResult, GameError> {
        self.handle_win_internal(winner_id, Some((discarder_id, tile)))
    }

    /// 处理胡牌（内部方法）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 胡牌玩家 ID
    /// - `discard_info`: 点炮信息（None 表示自摸，Some((discarder_id, tile)) 表示点炮胡）
    fn handle_win_internal(
        &mut self,
        player_id: u8,
        discard_info: Option<(u8, Tile)>,
    ) -> Result<ActionResult, GameError> {
        // 先检查是否可以胡牌（克隆数据以避免借用冲突）
        let hand = self.state.players[player_id as usize].hand.clone();
        let melds = self.state.players[player_id as usize].melds.clone();
        let melds_count = melds.len() as u8;
        
        let mut checker = WinChecker::new();
        let win_result = checker.check_win_with_melds(&hand, melds_count);
        
        if !win_result.is_win {
            return Err(GameError::InvalidAction);
        }
        
        // 设置动作触发标志
        let mut gang_pao_refund: Option<crate::game::settlement::SettlementResult> = None;
        
        if discard_info.is_none() {
            // 自摸
            self.state.check_zi_mo();
        } else {
            // 点炮胡，不是自摸
            if let Some((discarder_id, tile)) = discard_info {
                self.state.check_gang_pao(&tile, true);
                
                // 检查是否是杠上炮：点炮者是否刚刚杠过牌
                // 如果上一个动作是杠，且点炮者就是杠牌者，则需要退税
                if let Some(Action::Gang { .. }) = self.state.last_action {
                    let discarder = &self.state.players[discarder_id as usize];
                    // 检查点炮者是否有杠钱收入（说明刚刚杠过牌）
                    if discarder.gang_earnings > 0 {
                        // 执行杠上炮退税：点炮者把杠钱全部转交给胡牌者
                        use crate::game::settlement::GangSettlement;
                        let refund_amount = discarder.gang_earnings;
                        gang_pao_refund = Some(GangSettlement::calculate_gang_pao_refund(
                            discarder_id,
                            player_id,
                            refund_amount,
                        ));
                        
                        // 更新玩家杠钱收入（点炮者清零，胡牌者增加）
                        self.state.players[discarder_id as usize].gang_earnings = 0;
                        self.state.players[player_id as usize].add_gang_earnings(refund_amount);
                    }
                }
            }
        }
        self.state.check_gang_kai(true);
        self.state.check_hai_di();
        
        // 标记玩家离场
        let can_continue = BloodBattleRules::handle_player_out(player_id, &mut self.state);
        
        // 计算番数
        use crate::game::scoring::{RootCounter, Settlement};
        let roots = RootCounter::count_roots(&hand, &melds);
        let settlement = Settlement::calculate(&win_result, roots, &self.state.action_flags);
        
        Ok(ActionResult::Won {
            player_id,
            win_result,
            settlement,
            can_continue,
            discarder_id: discard_info.map(|(id, _)| id),
            gang_pao_refund, // 添加杠上炮退税信息
        })
    }

    /// 切换到下一个活跃玩家
    /// 
    /// 自动找到下一个未离场的玩家，更新 current_player 和 turn
    pub fn next_turn(&mut self) -> Result<(), GameError> {
        if let Some(next_player) = self.state.next_active_player() {
            self.state.current_player = next_player;
            self.state.turn += 1;
            Ok(())
        } else {
            Err(GameError::GameOver)
        }
    }

    /// 处理出牌后的响应（按优先级）
    /// 
    /// 优先级：胡 > 杠 > 碰 > 过
    /// 
    /// # 参数
    /// 
    /// - `discarder_id`: 出牌者 ID
    /// - `tile`: 打出的牌
    /// 
    /// # 返回
    /// 
    /// 如果有响应，返回处理结果；如果没有响应，返回 None
    pub fn handle_discard_responses(
        &mut self,
        discarder_id: u8,
        tile: Tile,
    ) -> Result<Option<ActionResult>, GameError> {
        // 收集所有可能的响应
        let mut responses = Vec::new();
        
        // 按顺序检查每个玩家（从出牌者的下家开始）
        let mut check_order = Vec::new();
        for i in 1..=3 {
            let player_id = (discarder_id + i) % 4;
            if !self.state.players[player_id as usize].is_out {
                check_order.push(player_id);
            }
        }
        
        // 检查每个玩家是否可以响应
        for player_id in &check_order {
            let player = &self.state.players[*player_id as usize];
            
            // 检查是否可以胡牌
            let mut test_hand = player.hand.clone();
            test_hand.add_tile(tile);
            let mut checker = WinChecker::new();
            let melds_count = player.melds.len() as u8;
            let win_result = checker.check_win_with_melds(&test_hand, melds_count);
            
            if win_result.is_win {
                // 检查缺一门和过胡限制
                use crate::engine::action_mask::ActionMask;
                use crate::game::scoring::BaseFansCalculator;
                let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
                let declared_suit = player.declared_suit;
                
                let mask = ActionMask::new();
                // 点炮胡，不是自摸
                if mask.can_win(
                    &test_hand,
                    &tile,
                    &self.state,
                    declared_suit,
                    base_fans,
                    false, // 点炮胡，不是自摸
                ) {
                    responses.push((*player_id, ActionResponse::Win));
                    // 胡牌优先级最高，找到第一个可以胡的玩家就处理
                    return self.handle_discard_win(*player_id, discarder_id, tile).map(Some);
                }
            }
            
            // 检查是否可以直杠
            if KongHandler::can_direct_kong(player, &tile).is_some() {
                responses.push((*player_id, ActionResponse::Kong));
            }
            
            // 检查是否可以碰
            if PongHandler::can_pong(player, &tile) {
                responses.push((*player_id, ActionResponse::Pong));
            }
        }
        
        // 如果没有胡牌响应，按优先级处理其他响应
        if !responses.is_empty() {
            return self.process_responses_by_priority(responses, discarder_id, tile);
        }
        
        Ok(None)
    }

    /// 按优先级处理响应
    /// 
    /// 优先级：杠 > 碰
    /// 
    /// # 参数
    /// 
    /// - `responses`: 响应列表
    /// - `discarder_id`: 出牌者 ID
    /// - `tile`: 打出的牌
    fn process_responses_by_priority(
        &mut self,
        responses: Vec<(u8, ActionResponse)>,
        _discarder_id: u8,
        tile: Tile,
    ) -> Result<Option<ActionResult>, GameError> {
        // 优先处理杠
        for (player_id, response) in &responses {
            if *response == ActionResponse::Kong {
                return self.handle_gang(*player_id, tile, false).map(Some);
            }
        }
        
        // 然后处理碰
        for (player_id, response) in &responses {
            if *response == ActionResponse::Pong {
                return self.handle_pong(*player_id, tile).map(Some);
            }
        }
        
        Ok(None)
    }

    /// 处理加杠（需要先检查抢杠胡）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 加杠玩家 ID
    /// - `tile`: 要加杠的牌
    /// 
    /// # 返回
    /// 
    /// 动作处理结果（如果被抢杠胡，返回胡牌结果）
    pub fn handle_add_kong(&mut self, player_id: u8, tile: Tile) -> Result<ActionResult, GameError> {
        // 先检查其他玩家是否可以抢杠胡
        for i in 0..4u8 {
            if i == player_id || self.state.players[i as usize].is_out {
                continue;
            }
            
            let other_player = &self.state.players[i as usize];
            if KongHandler::can_rob_kong(other_player, &tile, &other_player.melds) {
                // 被抢杠胡，取消加杠，处理抢杠胡
                self.state.check_qiang_gang(&tile, true);
                return self.handle_win_internal(i, Some((player_id, tile)));
            }
        }
        
        // 没有抢杠胡，执行加杠
        self.handle_gang(player_id, tile, false)
    }

    /// 游戏结束后的完整结算
    /// 
    /// 包括：查大叫、查花猪、退税
    /// 
    /// # 返回
    /// 
    /// 最终结算结果
    pub fn final_settlement(&self) -> FinalSettlementResult {
        use crate::game::settlement::FinalSettlement;
        use crate::game::scoring::{RootCounter, Settlement, BaseFansCalculator};
        use crate::tile::win_check::WinChecker;
        
        let mut all_settlements = Vec::new();
        
        // 1. 计算所有玩家的最终番数（用于查大叫和查花猪）
        let mut max_fans = 0u32;
        let mut ready_players_max_fans = 0u32;
        let mut ready_players = Vec::new();
        
        for player in &self.state.players {
            if player.is_out {
                continue;
            }
            
            // 检查是否听牌
            if player.is_ready {
                // 计算听牌玩家的最高可能番数
                // 这里简化处理，使用基础番数
                let mut checker = WinChecker::new();
                let test_result = checker.check_win(&player.hand);
                if test_result.is_win {
                    let base_fans = BaseFansCalculator::base_fans(test_result.win_type);
                    let roots = RootCounter::count_roots(&player.hand, &player.melds);
                    if let Some(total) = Settlement::new(base_fans, roots, 0).total_fans() {
                        ready_players_max_fans = ready_players_max_fans.max(total);
                        ready_players.push(player.id);
                    }
                }
                max_fans = max_fans.max(ready_players_max_fans);
            }
        }
        
        // 2. 查大叫（未听牌赔付）
        let not_ready_settlement = FinalSettlement::check_not_ready(
            &self.state.players,
            ready_players_max_fans,
        );
        if !not_ready_settlement.payments.is_empty() {
            all_settlements.push(not_ready_settlement);
        }
        
        // 3. 查花猪（未打完缺门赔付）
        let flower_pig_settlement = FinalSettlement::check_flower_pig(
            &self.state.players,
            max_fans,
        );
        if !flower_pig_settlement.payments.is_empty() {
            all_settlements.push(flower_pig_settlement);
        }
        
        // 4. 查大叫退税（流局时，没听牌的人必须把本局收到的所有杠钱退还）
        // 检查所有未听牌的玩家，无论是否杠过牌，都必须退还杠钱
        for player in &self.state.players {
            if !player.is_out && !player.is_ready {
                // 未听牌玩家必须退还所有杠钱
                let refund_amount = player.gang_earnings;
                if refund_amount > 0 {
                    // 找到原始支付者（所有非该玩家的其他玩家）
                    let original_payers: Vec<u8> = (0..4u8)
                        .filter(|&id| id != player.id && !self.state.players[id as usize].is_out)
                        .collect();
                    
                    if !original_payers.is_empty() {
                        let refund_settlement = FinalSettlement::refund_gang_money(
                            player.id,
                            refund_amount,
                            &original_payers,
                        );
                        all_settlements.push(refund_settlement);
                    }
                }
            }
        }
        
        // 5. 查花猪退税（如果杠牌者被查出花猪，也需要退税）
        // 注意：这里只处理杠牌者被查出花猪的情况，未听牌的杠牌者已在上面处理
        for gang_record in &self.state.gang_history {
            let gang_player = &self.state.players[gang_record.player_id as usize];
            
            // 如果杠牌者被查出花猪（且已听牌，因为未听牌已在上面处理），需要退税
            if !gang_player.is_out && gang_player.is_ready {
                let is_flower_pig = gang_player.has_declared_suit_tiles();
                
                if is_flower_pig && gang_player.gang_earnings > 0 {
                    // 找到原始支付者（所有非杠牌者）
                    let original_payers: Vec<u8> = (0..4u8)
                        .filter(|&id| id != gang_record.player_id && !self.state.players[id as usize].is_out)
                        .collect();
                    
                    if !original_payers.is_empty() {
                        let refund_amount = gang_player.gang_earnings;
                        let refund_settlement = FinalSettlement::refund_gang_money(
                            gang_record.player_id,
                            refund_amount,
                            &original_payers,
                        );
                        all_settlements.push(refund_settlement);
                    }
                }
            }
        }
        
        FinalSettlementResult {
            settlements: all_settlements,
        }
    }
}

/// 动作处理结果
#[derive(Debug, Clone)]
pub enum ActionResult {
    /// 摸牌
    Drawn { tile: Tile },
    /// 出牌
    Discarded { tile: Tile, responses: Vec<(u8, ActionResponse)> },
    /// 碰牌
    Ponged { tile: Tile },
    /// 杠牌
    Ganged { tile: Tile, kong_type: crate::game::kong::KongType, settlement: crate::game::settlement::SettlementResult },
    /// 胡牌
    Won { 
        player_id: u8, 
        win_result: crate::tile::win_check::WinResult, 
        settlement: crate::game::scoring::Settlement, 
        can_continue: bool,
        /// 点炮者 ID（None 表示自摸）
        discarder_id: Option<u8>,
        /// 杠上炮退税（如果有）
        gang_pao_refund: Option<crate::game::settlement::SettlementResult>,
    },
    /// 过
    Passed,
}

/// 动作响应
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionResponse {
    /// 可以胡
    Win,
    /// 可以杠
    Kong,
    /// 可以碰
    Pong,
}

impl Default for GameEngine {
    fn default() -> Self {
        Self::new()
    }
}

